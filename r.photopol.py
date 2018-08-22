#!/usr/bin/env python

from grass.pygrass.gis.region import Region
from grass.pygrass.utils import pixel2coor
from grass.pygrass import raster
from grass.script import array as garray
from grass import script
from grass.pygrass.vector.geometry import Point
import atexit
import numpy as np
from grass.exceptions import CalledModuleError
import sys
import os


OBS_ELEVATION = 1.75


#### temporary output rasters
tmp_rviewshed = "tmp_rviewshed"
tmp_observer  = "tmp_observer"
tmp_robserver = "tmp_robserver"
tmp_rcalc     = "tmp_rcalc_{}"
tmp_rdist_dis = "tmp_rdist_dis"
tmp_photopol  = "tmp_photopol"
tmp_res_lights = 'tmp_resamp_pixel'


TMP_MAPS=[tmp_rviewshed,
                tmp_observer,
                tmp_robserver,
                tmp_rcalc,
                tmp_rdist_dis,
                tmp_photopol,
                tmp_res_lights]                
                

def main():  
        
    elevation = sys.argv[1]
    nightlights = sys.argv[2]
    photopollution = sys.argv[3]
    max_distance= float(sys.argv[4])

    
    # Overwrite and verbose parameters
    #os.environ["GRASS_OVERWRITE"] = "1"
    os.environ['GRASS_VERBOSE']="-1"
        
    reg = Region() #get current region, use it for cell iteration
    if Region().nsres!=Region().ewres:
        print "ewres is different from nsres"
        raise SystemExit
    
    # open dem
    dem = raster.RasterRow(elevation)
    if  dem.is_open():
        dem.close()   
    if not dem.is_open():
        dem.open()
        
    # open night time lights       
    lights = raster.RasterRow(nightlights)
    
    if  lights.is_open():
        lights.close()   
        
    if not lights.is_open():
        lights.open()    
        
    script.use_temp_region()    #temporary region in case of parallel processing, maybe useless for current project
    
    # expand region according to viewshed max distance  (align to dem)
    script.run_command('g.region',n=reg.north+max_distance, s=reg.south-max_distance, e=reg.east+max_distance, w=reg.west-max_distance, align=elevation)
    
    # resample lights raster
    script.run_command("r.resample", input=nightlights, output=tmp_res_lights, overwrite=True)
    
    script.del_temp_region()


    calcPhotoPolRast(dem, max_distance,reg, elevation, lights ,photopollution)
    
    


def calcPhotoPol(row,col,reg, max_distance, elevation, lights, obs_elevation):
    y,x = pixel2coor((col, row),reg) # (col, row) = pixel, https://grass.osgeo.org/grass70/manuals/libpython/_modules/pygrass/utils.html#pixel2coor
    
    try:

        y=y-float(Region().nsres)/2 #pixel2coor returns upper left px coordinates, reposition observer at the centre of pixel
        x=x+float(Region().ewres)/2
        
        script.use_temp_region() 
        script.run_command('g.region',n=y+max_distance, s=y-max_distance, e=x+max_distance, w=x-max_distance, align=elevation)
                
        script.run_command('r.viewshed',
                                input=elevation, 
                                output=tmp_rviewshed, 
                                coordinates=(x,y),
                                max_distance =max_distance, 
                                observer_elevation=obs_elevation,               
                                overwrite =True,  flags= 'b')
               
        script.del_temp_region()
   
	
        # set region to viewshed       
        script.run_command( "r.null",  map= tmp_rviewshed,  setnull = 0)         
        script.use_temp_region()
        script.run_command( "g.region", raster =tmp_rviewshed, zoom=tmp_rviewshed) 
        
        # generate a new raster with NA in observer cell
        script.write_command("v.in.ascii", input="-", output=tmp_observer, stdin="{}|{}".format(x,y),overwrite=True) #https://grass.osgeo.org/grass70/manuals/libpython/script.html#script.core.write_command
        
        script.run_command( "v.to.rast", input=tmp_observer, output=tmp_robserver, use="cat", overwrite=True)     
        
        
        script.run_command("r.mapcalc", expression="\"{}\" = if(isnull (\"{}\"), 1, null ())".format(tmp_rcalc,tmp_robserver), overwrite=True)      
    
        #use tmp_rcalc raster as input in r.grow.distance to calculate distance from observer to other cells
        script.run_command("r.grow.distance",  flags="n",  input=tmp_rcalc, 
                                   distance=tmp_rdist_dis, 
                                   value="rdist.value",overwrite=True)
        
    
        # keep only cells that match viewshed analysis
        script.run_command("r.mask", raster=tmp_rviewshed, maskcats="1", overwrite=True)
    
        # calculate DN/distance
        script.run_command( "r.mapcalc", expression="\"{}\" = \"{}\" / \"{}\"".format(tmp_photopol, tmp_res_lights,tmp_rdist_dis), overwrite=True)
        
        process = script.parse_command("r.univar", map=tmp_photopol, flags='g')
        
        index_for_pixel=float(process[u'sum'])
        lights_DN= float(lights.get_value(Point(x, y), reg))#get night lights value   
    
    except:
        #in case of error, set pixel value to -999
        index_for_pixel = -999
        lights_DN = 0
        script.warning("Calculation failed for row:{},col:{}".format(row,col))
        
    finally:          
        script.run_command("r.mask", flags="r") # remove any mask        
        result=index_for_pixel+lights_DN
        script.del_temp_region()    
        return(result)
    

def calcPhotoPolRast(myraster, max_distance,reg, elevation, lights, photopollution):   
                 
    map2d_1 = garray.array()
    map2d_1.fill(np.nan)

    elev = raster.raster2numpy(elevation)
    elev= elev <> None 
   
    xcoords, ycoords =elev.nonzero()   
    
    counter = 1
    for pixel in zip(list(xcoords), list(ycoords)):
        
        i=pixel[0]
        j=pixel[1]
        
            
        indexForPixel = calcPhotoPol(i,j,reg=reg,elevation = elevation, lights=lights,max_distance=max_distance, obs_elevation=OBS_ELEVATION)
        map2d_1[i,j] = indexForPixel 
        
        perc=counter*100/len(xcoords)
        print 'pixel:{}/{} - {}%'.format(counter,len(xcoords), perc)
        counter += 1
    
    #write array object to grass raster map
    map2d_1.write(mapname=photopollution, overwrite=True) #SOS: region should be the same as generated map2d_1
    
    return ('map2d_1')


 
def cleanup():   
    #remove temporary rasters
    try:
        script.warning("Removing temporary rasters...")        
        script.run_command('g.remove', type='raster,vector', name=','.join(TMP_MAPS), flags='f', quiet = True)
    except:
         print("Unable to remove temporary files.")

    try:
        # remove any mask
        script.run_command("r.mask", flags="r") 
    except CalledModuleError:
        script.warning(_("Unable to remove mask."))

if __name__ == '__main__':
    atexit.register(cleanup)
    main()
    