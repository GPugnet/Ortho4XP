#!/usr/bin/env python3                                                       
##############################################################################
# Ortho4XP : A base mesh creation tool for the X-Plane 10 flight simulator.  #
# Version  : 1.18 released September 10th 2016                               #
# Copyright 2016 Oscar Pilote                                                #
# Thanks to all that have contributed to improvement of the code.            #
##############################################################################
#                                                                            #
#   LEGAL NOTICE :                                                           #
#                                                                            #
#   This program is free software: you can redistribute it and/or modify     #
#   it under the terms of the GNU General Public License as published by     #
#   the Free Software Foundation, either version 3 of the License, or        #
#   (at your option) any later version.                                      #
#                                                                            #
#   This program is distributed in the hope that it will be useful,          #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of           #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #
#   GNU General Public License for more details.                             #
#                                                                            #
#   You should have received a copy of the GNU General Public License        #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.    #
#                                                                            #
##############################################################################

version=' 1.18'

import os
import sys

try:
    import encodings.idna
except:
    pass
	
if getattr(sys,'frozen',False):
    Ortho4XP_dir        = '..'
else:
    Ortho4XP_dir        = '.'

try:
    sys.path.append(os.getcwd()+'/'+Ortho4XP_dir+'/bin/Modules')
except:
    pass
	
import requests

import threading,subprocess,time,gc,shutil,io
from math import *
import array,numpy

import random
import collections
import struct
import hashlib
from tkinter import *               # GUI
from tkinter import filedialog
import tkinter.ttk as ttk           # Themed Widgets
from PIL import Image, ImageDraw, ImageFilter, ImageTk
Image.MAX_IMAGE_PIXELS = 1000000000 # Not a decompression bomb attack!   
import subprocess 
import shlex

try:
    import gdal
    gdal_loaded = True
except:
    gdal_loaded = False

	
# The following are initialisation of the variables, they are then superseded by your Ortho4XP.cfg file but are here
# in case your config file misses some of then (evolution, edit, ...).  Do not modify them here but use your
# config file instead.


# Things that can be changed in the graphical interface
build_dir           = "default"     
default_website     = 'BI'
default_zl          = 16
sea_texture_params  = []       # example ['GO2',16], if you wish to use a different provider for the orthos over the sea (zonephoto tiles of french britany were done with this option)
min_area            =  0.01                                                            
curvature_tol       = 1
no_small_angles     = False
smallest_angle      = 5     # called min_angle in the graphical interface
skip_downloads      = False
skip_converts       = False
check_tms_response  = True  # Available as a checkbox in the interface, with it set to True some providers will lead to a dead loop of missed requests if data is not available. On the other hand with it set to False you may end up some times with a few corrupted textures with some white squares. 
verbose_output      = True
clean_tmp_files     = True
clean_unused_dds_and_ter_files = False
complex_masks       = False   # is set to True the build_masks process will be longer (because mesh from all nearby tiles will be used), but will not "suffer" from boundary effects
use_masks_for_inland= False   # if you want inland water to be treated like sea water (transparency based on a mask rather than fixed)
masks_width         = 8       # one unit is approximately 10m
ratio_water         = 0.2      
default_sniff_dir   = ''

#Things that are not in the interface
water_overlay       = True
water_option        = 3            # 1 = X-Plane, 2 = Photoreal only, 3 = Mixed 
sea_equiv           = []           # e.g. ['Étang de Berre','Estuaire de la Gironde','Lac Léman']
do_not_flatten_these_list  = []    # e.g. ['LFPG','LFMN'] , these will be kept as computed from the elevation file (and probably a bit bumpy)
tile_has_water_airport     = False # Put to True if an airport with a water boundary does not turn flat correctly
# NOTE that 'convert' from imagemagick is needed for the next color correction !!!
contrast_adjust       = {} # example {'BI':0,'FR':5,'IT':5}                                                       
brightness_adjust     = {} # example {'BI':0,'FR':-5,'IT':5}                                                     
saturation_adjust     = {} # example {'BI':0,'FR':10,'IT':10}                                                      
full_color_correction = {} # example {'CH':' -channel R -level 0%,100%,1.05 -channel B -level 0%,100%,0.97 '}
use_gimp=False
gimp_cmd="gimp "
Custom_scenery_dir=""
custom_scenery_prefix=""            # links in custom scenery will be of the form "custom_scenery_prefix"+zOrtho4XP_blablabla 
meshzl                      = 19    # The maximum ZL which the mesh will support (you can put a lower number if you do not need such zl)
hmin                        = 20    # Smallest triangle side-length
hmax                        = 2000  # Largest triangle side-length
water_smoothing             = 2     # increase if you find the rivers are not smooth enough
keep_old_pre_mask           = False # If set to True, then old unblured masks (whole_tile.png) are used directly without being regenerated before the bluring is made  (speed increase if set to True)
use_additional_water_shader = False # remainder of a test, which was not that succesful
use_decal_on_terrain        = False # if you want to use decal on top of the orthophoto, they can look good at small altitude
use_bing_for_non_existent_data = False # when using providers with local coverage only, if you ask for a zone not covered then Bing will be used there instead
overpass_server_list={"1":"http://api.openstreetmap.fr/oapi/interpreter", "2":"http://overpass-api.de/api/interpreter","3":"http://overpass.osm.rambler.ru/cgi/interpreter"}
overpass_server_choice="1"
keep_old_pre_mask   = False
use_additional_water_shader = False # remainder of a test, which was not that succesful
use_decal_on_terrain = False        # if you want to use decal on top of the orthophoto, they can look good at small altitude
dds_or_png          = 'dds'
tricky_provider_hack= 70000         # The minimum size a wms2048 image should be to be accepted (trying to avoid missed cached with white squares) 
wms_timeout         = 60
max_convert_slots   = 4     # Trying to use multi_core to convert jpegs into dds, adapt to your cpu capabilities
pools_max_points    = 65536 # do not change this !
normal_map_strength = 0.3   # shading due to slope is normally already present in an orthophoto, so 0 is orthophoto shade only and 1 is full additional shade
shutdown_timer      = 60    # Time in seconds to close program / shutdown computer after completition
shutd_msg_interval  = 15    # Shutdown message display interval




# Will be used as global variables
download_to_do_list=[]
convert_to_do_list=[]
busy_slots_mont=0
busy_slots_conv=0

if 'dar' in sys.platform:
    dir_sep         = '/'
    Triangle4XP_cmd = Ortho4XP_dir+"/Utils/Triangle4XP.app "
    copy_cmd        = "cp "
    delete_cmd      = "rm "
    rename_cmd      = "mv "
    unzip_cmd       = "7z "
    convert_cmd     = "convert " 
    convert_cmd_bis = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"nvcompress"+dir_sep+"nvcompress-mac-nocuda.app -bc1 " 
    gimp_cmd        = "gimp "
    devnull_rdir    = " >/dev/null 2>&1"
    use_gimp        = False
    # --> mth
    shutdown_cmd    = 'sudo shutdown -h now'
    # <-- mth
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/DSFTool.app')
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/Triangle4XP.app')
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/nvcompress/nvcompress-mac-nocuda.app')


elif 'win' in sys.platform: 
    dir_sep         = '\\'
    Triangle4XP_cmd = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"Triangle4XP.exe "
    copy_cmd        = "copy "
    delete_cmd      = "del "
    rename_cmd      = "move "
    unzip_cmd       = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"7z.exe "
    convert_cmd     = "convert " 
    convert_cmd_bis = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"nvcompress"+dir_sep+"nvcompress.exe -bc1 " 
    gimp_cmd        = "c:\\Program Files\\GIMP 2\\bin\\gimp-console-2.8.exe "
    showme_cmd      = Ortho4XP_dir+"/Utils/showme.exe "
    devnull_rdir    = " > nul  2>&1"
    use_gimp        = False
     # --> mth
    shutdown_cmd    = 'shutdown /s /f /t 0'
    # <-- mth

else:
    dir_sep         = '/'
    Triangle4XP_cmd = Ortho4XP_dir+"/Utils/Triangle4XP "
    delete_cmd      = "rm "
    copy_cmd        = "cp "
    rename_cmd      = "mv "
    unzip_cmd       = "7z "
    convert_cmd     = "convert " 
    convert_cmd_bis     = "nvcompress -fast -bc1a " 
    gimp_cmd        = "gimp "
    devnull_rdir    = " >/dev/null 2>&1 "
    use_gimp        = False
    # --> mth
    shutdown_cmd    = 'sudo shutdown -h now'
    # <-- mth
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/DSFTool')
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/Triangle4XP')

##############################################################################

dico_edge_markers   = {'outer':'1','inner':'1','coastline':'2',\
                       'tileboundary':'3','orthogrid':'3',\
                       'airport':'4','runway':'5','patch':'6'}
dico_tri_markers    = {'water':'1','sea':'2','sea_equiv':'3'} 

try:
    exec(open(Ortho4XP_dir+dir_sep+'Carnet_d_adresses.py').read())
except:
    print("The file Carnet_d_adresses.py does not follow the syntactic rules.")
    time.sleep(5)
    sys.exit()
 

##############################################################################
# Minimalist error messages.                                                 #
##############################################################################
##############################################################################
def usage(reason,do_i_quit=True):
    if reason=='config':
        print("The file Ortho4XP.cfg was not found or does not follow the "+\
              "syntactic rules.")
    elif reason=='command_line':
        print("The command line does not follow the syntactic rules.")
    elif reason=='osm_tags':
        print("I had a problem downloadings data from Openstreetmap.\n"+\
              "Your connection may be unavailable or the Overpass server\n"+\
              "may be unreachable.") 
    elif reason=='dem_files':
        print("!!!I could not fin the elevation data file, or it was broken.\n!!!I go on with all zero elevation (perhaps a tile full of sea ?)") 
    elif reason=='adresses':
        print("The file Carnet_d_adresses.py does not follow the syntactic"+\
              " rules.")
    elif reason=='crash':
        print("The mesh algorithm Triangle4XP has encountered a problem and"+\
              " had to stop.")
    elif reason=='inprogress':
        print("This functionality is not yet supported.")
    if do_i_quit==True:
            sys.exit()
    return
##############################################################################



##############################################################################
# Construction du fichier .poly décrivant toutes les données vectorielles
# a intégrer au maillage (frontières sol/eau et aéroports).
##############################################################################
def build_poly_file(lat0,lon0,option,build_dir): 
    t1=time.time()
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)
    strlat='{:+.0f}'.format(lat0).zfill(3)
    strlon='{:+.0f}'.format(lon0).zfill(4)
    if not os.path.exists(Ortho4XP_dir+dir_sep+"OSM_data"+dir_sep+strlat+strlon):
        os.makedirs(Ortho4XP_dir+dir_sep+"OSM_data"+dir_sep+strlat+strlon)
    poly_file     =  build_dir+dir_sep+'Data'+strlat+strlon+'.poly'
    airport_file  =  build_dir+dir_sep+'Data'+strlat+strlon+'.apt'
    patch_dir     =  Ortho4XP_dir+dir_sep+'Patches'+dir_sep+strlat+strlon
    dico_nodes={}
    dico_edges={}
    # seeds will serve to populate corresponding regions with the appropriate 
    # marker 
    water_seeds=[]
    sea_seeds=[]
    sea_equiv_seeds=[]
    flat_airport_seeds=[]
    flat_patch_seeds=[]
    sloped_patch_seeds=[]
    init_nodes=0
    tags=[]
    if option==2:  # Orthophoto only for inland water
        orthogrid=True
        print("-> Downloading airport and water/ground boundary data on Openstreetmap")
        tags.append('way["aeroway"="aerodrome"]')                                         
        tags.append('rel["aeroway"="aerodrome"]')                                         
        tags.append('way["aeroway"="heliport"]')                                         
        tags.append('way["natural"="coastline"]')
    else:  # Mixed
        orthogrid=True
        print("-> Downloading airport and water/ground boundary data from Openstreetmap :")
        tags.append('way["aeroway"="aerodrome"]')                                         
        tags.append('rel["aeroway"="aerodrome"]')                                         
        tags.append('way["aeroway"="heliport"]')                                         
        tags.append('way["natural"="water"]["tidal"!="yes"]')                                         
        tags.append('rel["natural"="water"]["tidal"!="yes"]')                                         
        tags.append('way["waterway"="riverbank"]')                                    
        tags.append('rel["waterway"="riverbank"]')                                    
        tags.append('way["natural"="coastline"]')
        tags.append('way["waterway"="dock"]')
    try:
        application.red_flag.set(0)
    except:
        pass
    for tag in tags:
        try:
            if application.red_flag.get()==1:
                print("\nOSM download process interrupted.")
                print('_____________________________________________________________'+\
                      '____________________________________')
                return
        except:
            pass
        subtags=tag.split('"')
        osm_filename=Ortho4XP_dir+dir_sep+"OSM_data"+dir_sep+strlat+strlon+dir_sep+strlat+strlon+'_'+subtags[0][0:-1]+'_'+\
                subtags[1]+'_'+subtags[3]+'.osm'
        osm_errors_filename=Ortho4XP_dir+dir_sep+"OSM_data"+dir_sep+strlat+strlon+dir_sep+strlat+strlon+'_'+subtags[0][0:-1]+'_'+\
                subtags[1]+'_'+subtags[3]+'_detected_errors.txt'
        if not os.path.isfile(osm_filename):
            print("    Obtaining OSM data for "+tag)
            s=requests.Session()
            osm_download_ok = False
            while osm_download_ok != True:
                url=overpass_server_list[overpass_server_choice]+"?data=("+tag+"("+str(lat0)+","+str(lon0)+","+str(lat0+1)+","+str(lon0+1)+"););(._;>>;);out meta;"
                r=s.get(url)
                if r.headers['content-type']=='application/osm3s+xml':
                    osm_download_ok=True
                else:
                    print("      OSM server was busy, new tentative...")
            osmfile=open(osm_filename,'wb')
            osmfile.write(r.content)
            osmfile.close()
            print("     Done.")
        else:
            print("    Recycling OSM data for "+tag)
        if 'way[' in tag:
            [dicosmw,dicosmw_name,dicosmw_icao,dicosmw_ele]=osmway_to_dicos(osm_filename)
        elif 'rel[' in tag:
            [dicosmr,dicosmrinner,dicosmrouter,dicosmr_name,dicosmr_icao,dicosmr_ele]=osmrel_to_dicos(osm_filename,osm_errors_filename)

        # we shall treat osm data differently depending on tag 
        if tag=='way["aeroway"="aerodrome"]' or tag=='way["aeroway"="heliport"]':
            sloped_airports_list=[]
            if os.path.exists(patch_dir):
                for pfilename in os.listdir(patch_dir):
                    if pfilename[-10:] == '.patch.osm':
                        sloped_airports_list.append(pfilename[:4])
            for wayid in dicosmw:
                way=dicosmw[wayid]
                # we only treat closed ways, non closed should not exist in 
                # osm ways (but a few sometimes do!)
                if strcode(way[0]) == strcode(way[-1]):
                    signed_area=area(way)
                    if signed_area<0:
                        side='left'
                    else:
                        side='right'
                    keep_that_one=True
                    if (wayid in dicosmw_icao) and (wayid in dicosmw_name):
                        print("       * "+dicosmw_icao[wayid]+" "+dicosmw_name[wayid])
                    elif (wayid in dicosmw_icao):
                        print("       * "+dicosmw_icao[wayid])
                    elif (wayid in dicosmw_name):
                        print("       *      "+dicosmw_name[wayid])
                    else:
                        print("       * lat="+str(way[0][0])+" lon="+str(way[0][1]))
                    if (wayid in dicosmw_ele):
                        altitude=dicosmw_ele[wayid]
                    else:
                        altitude='unknown'
                    if (wayid in dicosmw_icao):
                        if (dicosmw_icao[wayid] in sloped_airports_list) or (dicosmw_icao[wayid] in do_not_flatten_these_list):
                            print("          I will not flatten "+dicosmw_icao[wayid]+ " airport.")
                            keep_that_one=False
                    if keep_that_one==True:
                        keep_way(way,lat0,lon0,1,'airport',dico_nodes,\
                                dico_edges)
                        flat_airport_seeds.append([way,\
                                pick_point_check(way,side,lat0,lon0),altitude])
                else:
                    print("One of the airports within the tile is not correctly closed \n"+\
                          "on Openstreetmap ! Close to coordinates " + str(way[0]))
        elif tag=='rel["aeroway"="aerodrome"]':
            sloped_airports_list=[]
            if os.path.exists(patch_dir):
                for pfilename in os.listdir(patch_dir):
                    if pfilename[-10:] == '.patch.osm':
                        sloped_airports_list.append(pfilename[:4])
            for relid in dicosmr:
                keep_that_one=True
                if (relid in dicosmr_icao):
                    if dicosmr_icao[relid] in sloped_airports_list or (dicosmr_icao[relid] in do_not_flatten_these_list):
                        keep_that_one=False
                if (relid in dicosmr_icao) and (relid in dicosmr_name):
                    print("       * "+dicosmr_icao[relid]+" "+dicosmr_name[relid])
                elif (relid in dicosmr_icao):
                    print("       * "+dicosmr_icao[relid])
                elif relid in dicosmr_name:
                        print("       *      "+dicosmr_name[relid])
                if (relid in dicosmr_ele):
                    altitude=dicosmr_ele[relid]
                else:
                    altitude='unknown'
                if keep_that_one==False:
                    continue
                for waypts in dicosmrinner[relid]:
                    keep_way(waypts,lat0,lon0,1,'airport',dico_nodes,\
                                        dico_edges)
                for waypts in dicosmrouter[relid]:
                    signed_area=area(waypts)
                    if signed_area<0:
                        side='left'
                    else:
                        side='right'
                    keep_way(waypts,lat0,lon0,1,'airport',dico_nodes,\
                                        dico_edges)
                    flat_airport_seeds.append([waypts,\
                            pick_point_check(waypts,side,lat0,lon0),altitude])
        elif 'way["natural"="coastline"]' in tag:
            total_sea_seeds=0
            for wayid in dicosmw:
                way=dicosmw[wayid]
                # Openstreetmap ask that sea is to the right of oriented
                # coastline. We trust OSM contributors...
                if strcode(way[0])!=strcode(way[-1]):
                    if (lat0>=40 and lat0<=49 and lon0>=-93 and lon0<=-76):
                        sea_equiv_seeds+=pick_points_safe(way,'right',lat0,lon0)
                    else:
                        sea_seeds+=pick_points_safe(way,'right',lat0,lon0)
                    total_sea_seeds+=1
                keep_way(way,lat0,lon0,1,'coastline',dico_nodes,dico_edges)
            if total_sea_seeds<=3:
                for wayid in dicosmw:
                    way=dicosmw[wayid]
                    if strcode(way[0])==strcode(way[-1]):
                        if (lat0>=40 and lat0<=49 and lon0>=-93 and lon0<=-76):
                            sea_equiv_seeds+=pick_points_safe(way,'right',lat0,lon0)
                        else:
                            sea_seeds+=pick_points_safe(way,'right',lat0,lon0)
        elif ('way["natural"="water"]' in tag) or ('way["waterway"="riverbank"]' in tag) or ('way["waterway"="dock"]' in tag) :
            efile=open(osm_errors_filename,'w')
            osm_errors_found=False
            for wayid in dicosmw:
                #print(wayid)
                way=dicosmw[wayid]
                if strcode(way[0]) != strcode(way[-1]):
                    osm_errors_found=True
                    efile.write("Way id="+str(wayid)+" was not treated because it is not closed.\n")
                    continue
                if touches_region(way,lat0,lat0+1,lon0,lon0+1):
                    signed_area=area(way)
                    # Keep only sufficiently large water pieces. 1 deg^2 is
                    # very roughly equal to 10000 km^2
                    if abs(signed_area) >= min_area/10000.0: 
                        if signed_area<0:
                            side='left'
                        else:
                            side='right'
                        keep_way(way,lat0,lon0,1,'outer',dico_nodes,\
                                dico_edges)
                        points_checked=pick_points_safe(way,side,lat0,lon0,check=True)
                        #print(points_checked)
                        sea_way=False
                        try:
                            if dicosmw_name[wayid] in sea_equiv:
                                print("     Sea_equiv found :",dicosmw_name[wayid])
                                sea_way=True
                        except:
                            pass    
                        if sea_way!=True:
                            water_seeds+=points_checked
                        else:
                            sea_equiv_seeds+=points_checked
            efile.close()
            if osm_errors_found:
                print("     !!!Some OSM errors were detected!!!\n        They are listed in "+str(osm_errors_filename))
            else:
                os.remove(osm_errors_filename)
        elif 'rel[' in tag:
            for relid in dicosmr:
                sea_rel=False
                try:
                    if dicosmr_name[relid] in sea_equiv:
                        print("     Sea_equiv found :",dicosmr_name[relid])
                        sea_rel=True
                except:
                    pass    
                for waypts in dicosmrinner[relid]:
                    keep_way(waypts,lat0,lon0,1,'inner',dico_nodes,\
                                        dico_edges)
                for waypts in dicosmrouter[relid]:
                    signed_area=area(waypts)
                    if abs(signed_area) >= min_area/10000.0: 
                        if signed_area<0:
                            side='left'
                        else:
                            side='right'
                        keep_way(waypts,lat0,lon0,1,'outer',dico_nodes,\
                                        dico_edges)
                        points_checked=pick_points_safe(waypts,side,lat0,lon0,check=True)
                        if sea_rel!=True:
                            water_seeds+=points_checked
                        else:
                            sea_equiv_seeds+=points_checked
    treated_nodes=len(dico_nodes)-init_nodes
    init_nodes=len(dico_nodes)
    if treated_nodes>0:
        strtmp=str(treated_nodes)+" new nodes."
    else:
        strtmp="no new node."
    print("   -> process of the associated data completed : "+strtmp)
    print("-> Cutting off of too long edges,")
    dico_edges_tmp={}
    for edge in dico_edges:
        [initpt,endpt]=edge.split('|')
        xi=xcoord(initpt,dico_nodes)
        yi=ycoord(initpt,dico_nodes)
        xf= xcoord(endpt,dico_nodes)
        yf= ycoord(endpt,dico_nodes)
        #length=sqrt((xi-xf)*(xi-xf)+(yi-yf)*(yi-yf))
        length=abs(xi-xf)+abs(yi-yf)
        pieces=ceil(length*1000)
        if pieces == 1:
            dico_edges_tmp[edge]=dico_edges[edge]
        else:
            coordlist=[]
            for k in range(1,pieces):
                xk=((pieces-k)/pieces)*xi+(k/pieces)*xf
                yk=((pieces-k)/pieces)*yi+(k/pieces)*yf
                coordlist.append([xk,yk])
                keep_node_xy(xk,yk,lat0,lon0,dico_nodes)
            keep_edge_str_tmp(initpt,strxy(coordlist[0][0],coordlist[0][1],\
                    lat0,lon0),dico_edges[edge],dico_edges_tmp)
            for k in range(1,pieces-1):
                keep_edge_str_tmp(strxy(coordlist[k-1][0],coordlist[k-1][1],\
                        lat0,lon0),strxy(coordlist[k][0],coordlist[k][1],\
                        lat0,lon0),dico_edges[edge],dico_edges_tmp)
            keep_edge_str_tmp(strxy(coordlist[pieces-2][0],\
                    coordlist[pieces-2][1],lat0,lon0),endpt,dico_edges[edge],\
                        dico_edges_tmp)
    dico_edges=dico_edges_tmp
    print("-> Adding patch data for the mesh, ")
    if os.path.exists(patch_dir):
        patchlist=os.listdir(patch_dir)
    else:
        patchlist=[]
    for pfilename in patchlist:
        if pfilename[-10:] != '.patch.osm':
            continue
        pfile=open(patch_dir+dir_sep+pfilename,"r")
        secondline=pfile.readline()
        secondline=pfile.readline()
        print("     "+pfilename)
        finished_with_nodes=False
        started_with_nodes=False
        nodes_codes={}
        while not finished_with_nodes==True:
            items=pfile.readline().split()
            if '<node' in items:
                started_with_nodes=True
                for item in items:
                    if 'id=' in item:
                        id=item[3:]
                    elif 'lat=' in item:
                        slat=item[5:-1]
                    elif 'lon=' in item:
                        slon=item[5:-1]
                dico_nodes[slat+'_'+slon]=[float(slon)-lon0,float(slat)-lat0]
                nodes_codes[id]=slat+'_'+slon
            elif started_with_nodes==True:
                finished_with_nodes=True
        finished_with_ways=False
        while finished_with_ways != True:
            newwaycodes=[]
            finished_with_newway=False
            flat_patch=False
            sloped_patch=False
            way_profile='atanh'
            way_steepness='3.5'
            way_cell_size='5'
            while finished_with_newway!=True:
                line=pfile.readline().split()
                if '<nd' in line:
                    newnodeid=line[1][4:]
                    newwaycodes.append(nodes_codes[newnodeid])
                else:
                    if "k='altitude'" in line:
                        flat_patch=True
                        if line[2][3:-1]=='mean':
                            way_altitude='mean'
                        else:
                            way_altitude=float(line[2][3:-1])
                    elif "k='altitude_high'" in line:
                        sloped_patch=True
                        way_altitude_high=float(line[2][3:-1]) 
                    elif "k='altitude_low'" in line:
                        way_altitude_low=float(line[2][3:-1])
                    elif "k='profile'" in line:
                        way_profile=line[2][3:-1]
                    elif "k='steepness'" in line:
                        way_steepness=line[2][3:-1]
                    elif "k='cell_size'" in line:
                        way_cell_size=line[2][3:-1]
                    elif '</way>' in line:
                        finished_with_newway=True
                    else:
                        pass
            if flat_patch==True:
                seed=keep_patch(newwaycodes,dico_nodes,dico_edges)
                flat_patch_seeds.append([seed,way_altitude,newwaycodes])
            elif sloped_patch==True:
                [seed,xi,yi,xf,yf]=keep_sloped_patch(newwaycodes,\
                        float(way_cell_size)/100000,dico_nodes,\
                        dico_edges,lat0,lon0)
                sloped_patch_seeds.append([seed,xi,yi,xf,yf,\
                        way_altitude_high,way_altitude_low,\
                        way_profile,way_steepness,way_cell_size])
            else:
                seed=keep_patch(newwaycodes,dico_nodes,dico_edges)
            line=pfile.readline().split()
            if '</osm>' in line:
                finished_with_ways=True
        # Now we need to sanitize edges because the cuts which we made
        # on the short sides of sloped patches may be encroached with
        # sides of flat patches.
        pfile.seek(0)
        finished_with_nodes=False
        started_with_nodes=False
        while not finished_with_nodes==True:
            items=pfile.readline().split()
            if '<node' in items:
                started_with_nodes=True
            elif started_with_nodes==True:
                finished_with_nodes=True
        finished_with_ways=False
        while finished_with_ways != True:
            newwaycodes=[]
            finished_with_newway=False
            sloped_patch=False
            while finished_with_newway!=True:
                line=pfile.readline().split()
                if '<nd' in line:
                    newnodeid=line[1][4:]
                    newwaycodes.append(nodes_codes[newnodeid])
                else:
                    if "k='altitude_high'" in line:
                        sloped_patch=True
                    elif '</way>' in line:
                        finished_with_newway=True
                    else:
                        pass
            if sloped_patch==True:
                dico_edges.pop(newwaycodes[0]+'|'+newwaycodes[3],None)
                dico_edges.pop(newwaycodes[3]+'|'+newwaycodes[0],None)
                dico_edges.pop(newwaycodes[1]+'|'+newwaycodes[2],None)
                dico_edges.pop(newwaycodes[2]+'|'+newwaycodes[1],None)
            line=pfile.readline().split()
            if '</osm>' in line:
                finished_with_ways=True
        pfile.close()
    print("-> Adding of edges related to the orthophoto grid and computation of\n"
          "     their intersections with OSM edges,")
    dico_edges=cut_edges_with_grid(lat0,lon0,dico_nodes,dico_edges,orthogrid)
    print("     Removal of obsolete edges,")
    dico_edges_tmp={}
    for edge in dico_edges:
        [initpt,endpt]=edge.split('|')
        if initpt != endpt:
            dico_edges_tmp[edge]=dico_edges[edge]
        #else:
        #    print("one removed edge : "+str(initpt))
    dico_edges=dico_edges_tmp
    print("     Removal of obsolete nodes,")
    final_nodes={}
    for edge in dico_edges:
        #print(edge)
        [initpt,endpt]=edge.split('|')
        final_nodes[initpt]=dico_nodes[initpt]
        final_nodes[endpt]=dico_nodes[endpt]
    dico_nodes=final_nodes
    print("-> Transcription of the updated data to the file "+poly_file)
    total_nodes=len(dico_nodes)
    f=open(poly_file,'w')
    f.write(str(total_nodes)+' 2 0 0\n')
    dico_node_pos={}
    idx=1
    for key in dico_nodes:
        dico_node_pos[key]=idx
        f.write(str(idx)+' '+str(dico_nodes[key][0])+' '+\
          str(dico_nodes[key][1])+'\n')        
        idx+=1
    f.write('\n')
    idx=1
    total_edges=len(dico_edges)
    f.write(str(total_edges)+' 1\n')
    for edge in dico_edges:
        [code1,code2]=edge.split('|')
        idx1=dico_node_pos[code1]
        idx2=dico_node_pos[code2]
        f.write(str(idx)+' '+str(idx1)+' '+str(idx2)+' '+\
                dico_edge_markers[dico_edges[edge]]+'\n')
        idx+=1
    f.write('\n0\n')
    total_seeds=len(water_seeds)+len(sea_seeds)+len(sea_equiv_seeds)+\
                len(flat_airport_seeds)+len(flat_patch_seeds)+\
                len(sloped_patch_seeds)
    if total_seeds==0:
        if sea_texture_params=='':
            water_seeds.append([1000,1000])
        else:
            sea_seeds.append([lon0+0.5,lat0+0.5])
        total_seeds=1
    f.write('\n'+str(total_seeds)+' 1\n')
    idx=1
    for seed in water_seeds:
        f.write(str(idx)+' '+str(seed[0]-lon0)+' '+str(seed[1]-lat0)+' '+\
          dico_tri_markers['water']+'\n')
        idx+=1
    for seed in sea_seeds:
        f.write(str(idx)+' '+str(seed[0]-lon0)+' '+str(seed[1]-lat0)+' '+\
          dico_tri_markers['sea']+'\n')
        idx+=1
    for seed in sea_equiv_seeds:
        f.write(str(idx)+' '+str(seed[0]-lon0)+' '+str(seed[1]-lat0)+' '+\
          dico_tri_markers['sea_equiv']+'\n')
        idx+=1
    apt_idx=100 
    for seed in flat_airport_seeds:
        f.write(str(idx)+' '+str(seed[1][0]-lon0)+' '+\
          str(seed[1][1]-lat0)+' '+str(apt_idx)+'\n')
        apt_idx+=1        
        idx+=1
    fp_idx=1000
    for seed in flat_patch_seeds:
        f.write(str(idx)+' '+str(seed[0][0])+' '+\
          str(seed[0][1])+' '+str(fp_idx)+'\n')
        fp_idx+=1
        idx+=1
    sp_idx=10000
    for seed in sloped_patch_seeds:
        f.write(str(idx)+' '+str(seed[0][0])+' '+str(seed[0][1])+' '+\
                str(sp_idx)+'\n')
        sp_idx+=1
    print("   Remain " + str(len(dico_edges))+\
          " edges in total.") 
    f.close()
    f=open(airport_file,"w")
    apt_idx =   100
    fp_idx  =  1000
    sp_idx  = 10000
    for seed in flat_airport_seeds:
        f.write("Airport "+str(apt_idx)+" : "+str(len(seed[0]))+\
                " nodes.\n")
        f.write("Elevation "+str(seed[2])+'\n')
        for node in seed[0]:
            f.write(str(float(node[0]))+" "+str(float(node[1]))+"\n")
        f.write("\n")
        apt_idx+=1
    f.write('\n')
    for seed in flat_patch_seeds:
        f.write("Flat_patch "+str(fp_idx)+" : "+str(len(seed[2]))+"\n") 
        f.write("Elevation "+str(seed[1])+'\n')
        for node in seed[2]:
            [slat,slon]=node.split('_')
            f.write(slat+" "+slon+"\n")
        f.write("\n")
        fp_idx+=1
    f.write('\n')
    for seed in sloped_patch_seeds:
        f.write("Sloped_patch "+str(sp_idx)+" : "+str(seed[1])+" "+\
                str(seed[2])+" "+str(seed[3])+" "+str(seed[4])+" "+\
                str(seed[5])+" "+str(seed[6])+" "+str(seed[7])+" "+\
                str(seed[8])+" "+str(seed[9])+"\n") 
        sp_idx+=1
    f.close()
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-t1))+\
                'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
    
    return 
#############################################################################

##############################################################################
def osmway_to_dicos(osm_filename):
    pfile=open(osm_filename,'r',encoding="utf-8")
    dicosmn={}
    dicosmw={}
    dicosmw_name={}
    dicosmw_icao={}
    dicosmw_ele={}
    finished_with_file=False
    in_way=False
    first_line=pfile.readline()
    if "'" in first_line:
        separator="'"
    else:
        separator='"'
    while not finished_with_file==True:
        items=pfile.readline().split(separator)
        #if items[0]=='  <node id=':
        if '<node id=' in items[0]:
            id=items[1]
            for j in range(0,len(items)):
                if items[j]==' lat=':
                    slat=items[j+1]
                elif items[j]==' lon=':
                    slon=items[j+1]
            #slat=items[3]
            #slon=items[5]
            dicosmn[id]=[slat,slon]
        #elif items[0]=='  <way id=':
        elif '<way id=' in items[0]:
            in_way=True
            wayid=items[1]
            dicosmw[wayid]=[]  
        #elif items[0]=='    <nd ref=':
        elif '<nd ref=' in items[0]:
            dicosmw[wayid].append(dicosmn[items[1]])
        #elif items[0]=='    <tag k=' and in_way and items[1]=='name':
        elif '<tag k=' in items[0] and in_way and items[1]=='name':
            dicosmw_name[wayid]=items[3]
        #elif items[0]=='    <tag k=' and in_way and items[1]=='icao':
        elif '<tag k=' in items[0] and in_way and items[1]=='icao':
            dicosmw_icao[wayid]=items[3]
        #elif items[0]=='    <tag k=' and in_way and items[1]=='ele':
        elif '<tag k=' in items[0] and in_way and items[1]=='ele':
            dicosmw_ele[wayid]=items[3]
        #elif items[0]=='</osm>\n':
        elif '</osm>' in items[0]:
            finished_with_file=True
    pfile.close()
    print("     A total of "+str(len(dicosmn))+" node(s) and "+str(len(dicosmw))+" way(s).")
    return [dicosmw,dicosmw_name,dicosmw_icao,dicosmw_ele]
##############################################################################

##############################################################################
def osmrel_to_dicos(osm_filename,osm_errors_filename):
    pfile=open(osm_filename,'r',encoding="utf-8")
    efile=open(osm_errors_filename,'w')
    osm_errors_found=False
    dicosmn={}
    dicosmw={}
    dicosmr={}
    dicosmrinner={}
    dicosmrouter={}
    dicosmr_name={}
    dicosmr_icao={}
    dicosmr_ele={}
    dicoendpt={}
    finished_with_file=False
    in_rel=False
    first_line=pfile.readline()
    if "'" in first_line:
        separator="'"
    else:
        separator='"'
    while not finished_with_file==True:
        items=pfile.readline().split(separator)
        #if items[0]=='  <node id=':
        if '<node id=' in items[0]:
            id=items[1]
            for j in range(0,len(items)):
                if items[j]==' lat=':
                    slat=items[j+1]
                elif items[j]==' lon=':
                    slon=items[j+1]
            dicosmn[id]=[slat,slon]
        #elif items[0]=='  <way id=':
        elif '<way id=' in items[0]:
            wayid=items[1]
            dicosmw[wayid]=[]  
        #elif items[0]=='    <nd ref=':
        elif '<nd ref=' in items[0]:
            dicosmw[wayid].append(items[1])
        #elif items[0]=='  <relation id=':
        elif '<relation id=' in items[0]:
            relid=items[1]
            in_rel=True
            dicosmr[relid]=[]
            dicosmrinner[relid]=[]
            dicosmrouter[relid]=[]
            dicoendpt={}
        #elif items[0]=='    <member type=':
        elif '<member type=' in items[0]:
            if items[1]!='way':
                efile.write("Relation id="+str(relid)+" contains member "+items[1]+" which was not treated because it is not a way.\n")
                osm_errors_found=True
                continue
            role=items[5]
            if role=='inner':
                waytmp=[]
                for nodeid in dicosmw[items[3]]:
                    waytmp.append(dicosmn[nodeid])
                dicosmrinner[relid].append(waytmp)
            elif role=='outer':
                endpt1=dicosmw[items[3]][0]
                endpt2=dicosmw[items[3]][-1]
                if endpt1==endpt2:
                    waytmp=[]
                    for nodeid in dicosmw[items[3]]:
                        waytmp.append(dicosmn[nodeid])
                    dicosmrouter[relid].append(waytmp)
                else:
                    if endpt1 in dicoendpt:
                        dicoendpt[endpt1].append(items[3])
                    else:
                        dicoendpt[endpt1]=[items[3]]
                    if endpt2 in dicoendpt:
                        dicoendpt[endpt2].append(items[3])
                    else:
                        dicoendpt[endpt2]=[items[3]]
            else:
                efile.write("Relation id="+str(relid)+" contains a member with role different from inner or outer, it was not treated.\n")
                osm_errors_found=True
                continue
            dicosmr[relid].append(items[3]) 
        #elif items[0]=='    <tag k=' and in_rel and items[1]=='name':
        elif '<tag k=' in items[0] and in_rel and items[1]=='name':
            dicosmr_name[relid]=items[3]
        #elif items[0]=='    <tag k=' and in_rel and items[1]=='icao':
        elif '<tag k=' in items[0] and in_rel and items[1]=='icao':
            dicosmr_icao[relid]=items[3]
        #elif items[0]=='    <tag k=' and in_rel and items[1]=='ele':
        elif '<tag k=' in items[0] and in_rel and items[1]=='ele':
            dicosmr_ele[relid]=items[3]
        #elif items[0]=='  </relation>\n':
        elif '</relation>' in items[0]:
            bad_rel=False
            for endpt in dicoendpt:
                if len(dicoendpt[endpt])!=2:
                    bad_rel=True
                    break
            if bad_rel==True:
                efile.write("Relation id="+str(relid)+" is ill formed and was not treated.\n")
                osm_errors_found=True
                dicosmr.pop(relid,'None')
                dicosmrinner.pop(relid,'None')
                dicosmrouter.pop(relid,'None')
                continue
            while dicoendpt:
                waypts=[]
                endpt=next(iter(dicoendpt))
                way=dicoendpt[endpt][0]
                endptinit=dicosmw[way][0]
                endpt1=endptinit
                endpt2=dicosmw[way][-1]
                for node in dicosmw[way][:-1]:
                    waypts.append(dicosmn[node])
                while endpt2!=endptinit:
                    if dicoendpt[endpt2][0]==way:
                            way=dicoendpt[endpt2][1]
                    else:
                            way=dicoendpt[endpt2][0]
                    endpt1=endpt2
                    if dicosmw[way][0]==endpt1:
                        endpt2=dicosmw[way][-1]
                        for node in dicosmw[way][:-1]:
                            waypts.append(dicosmn[node])
                    else:
                        endpt2=dicosmw[way][0]
                        for node in dicosmw[way][-1:0:-1]:
                            waypts.append(dicosmn[node])
                    dicoendpt.pop(endpt1,'None')
                waypts.append(dicosmn[endptinit])
                dicosmrouter[relid].append(waypts)
                dicoendpt.pop(endptinit,'None')
            dicoendpt={}
        #elif items[0]=='</osm>\n':
        elif '</osm>' in items[0]:
            finished_with_file=True
    pfile.close()
    efile.close()
    print("     A total of "+str(len(dicosmn))+" node(s) and "+str(len(dicosmr))+" relation(s).")
    if osm_errors_found:
        print("     !!!Some OSM errors were detected!!!\n        They are listed in "+str(osm_errors_filename))
    else:
        os.remove(osm_errors_filename)
    return [dicosmr,dicosmrinner,dicosmrouter,dicosmr_name,dicosmr_icao,dicosmr_ele]
##############################################################################

#############################################################################
def strcode(node):
   return node[0]+'_'+node[1]
#############################################################################


#############################################################################
def keep_node(node,lat0,lon0,dico_nodes):
   dico_nodes[strcode(node)]=[float(node[1])-lon0,float(node[0])-lat0]
   return
#############################################################################
   
#############################################################################
def keep_edge(node0,node,marker,dico_edges):
   if strcode(node0) != strcode(node):
       if strcode(node)+'|'+strcode(node0) in dico_edges:
           dico_edges[strcode(node)+'|'+strcode(node0)]=marker
       else:
           dico_edges[strcode(node0)+'|'+strcode(node)]=marker
   return
#############################################################################

#############################################################################
def keep_way(way,lat0,lon0,sign,marker,dico_nodes,dico_edges):
   if sign==1:
       node0=way[0]
       keep_node(node0,lat0,lon0,dico_nodes)
       for node in way[1:]:
           keep_node(node,lat0,lon0,dico_nodes)
           keep_edge(node0,node,marker,dico_edges)
           node0=node
   elif sign==-1:
       node0=way[-1]
       keep_node(node0,lat0,lon0,dico_nodes)
       for node in way[-1:-len(way)-1:-1]:
           keep_node(node,lat0,lon0,dico_nodes)
           keep_edge(node0,node,marker,dico_edges)
           node0=node
   return
#############################################################################
   
#############################################################################
def strxy(x,y,lat0,lon0):
    return str(y+lat0)+'_'+str(x+lon0)
#############################################################################

#############################################################################
def keep_node_xy(x,y,lat0,lon0,dico_nodes):
   dico_nodes[strxy(x,y,lat0,lon0)]=[x,y]
   return
#############################################################################

#############################################################################
def xcoord(strcode,dico_nodes):
    return float(dico_nodes[strcode][0])
#############################################################################

#############################################################################
def ycoord(strcode,dico_nodes):
    return float(dico_nodes[strcode][1])
#############################################################################
   
#############################################################################
def keep_edge_str_tmp(strcode1,strcode2,marker,dico_edges_tmp):
   dico_edges_tmp[strcode1+'|'+strcode2]=marker
   return
#############################################################################


#############################################################################
def keep_patch(newwaycodes,dico_nodes,dico_edges):
    for i in range(0,len(newwaycodes)-1):
        dico_edges[newwaycodes[i]+'|'+newwaycodes[i+1]]='patch'
    eps=0.01
    newway=[]
    for node_code in newwaycodes:
        newway+=dico_nodes[node_code]
    testpt1=[(newway[0]+newway[2])/2.0+eps*(newway[3]-newway[1]),\
             (newway[1]+newway[3])/2.0-eps*(newway[2]-newway[0])]
    testpt2=[(newway[0]+newway[2])/2.0-eps*(newway[3]-newway[1]),\
             (newway[1]+newway[3])/2.0+eps*(newway[2]-newway[0])]
    if point_in_polygon(testpt1,newway)==True:
        return testpt1
    else:
        return testpt2
#############################################################################


#############################################################################
def keep_sloped_patch(waycodes,cell_size,dico_nodes,dico_edges,lat0,lon0):
    way=[]
    sdn={}
    for node_code in waycodes:
        way+=dico_nodes[node_code]
    approx_length=sqrt((way[0]-way[2])**2*cos(lat0*pi/180)**2+\
            (way[1]-way[3])**2)
    approx_width =sqrt((way[0]-way[6])**2*cos(lat0*pi/180)**2+\
            (way[1]-way[7])**2)
    Nx=ceil(approx_width/cell_size)
    Ny=ceil(approx_length/cell_size)
    for ny in range(0,Ny+1):
        for nx in range(0,Nx+1):
            xcoord=way[0]+ny/Ny*(way[2]-way[0])+nx/Nx*\
                    (way[6]-way[0]+ny/Ny*(way[0]+way[4]-way[2]-way[6]))
            ycoord=way[1]+ny/Ny*(way[3]-way[1])+nx/Nx*\
                    (way[7]-way[1]+ny/Ny*(way[1]+way[5]-way[3]-way[7]))
            nlat=ycoord+lat0
            nlon=xcoord+lon0
            if (nx!=0 or ny!=0) and (nx!=0 or ny!=Ny) and \
                    (nx!=Nx or ny!=0) and (nx!=Nx or ny!=Ny):
                dico_nodes[str(nlat)+'_'+str(nlon)]=[xcoord,ycoord]
                sdn[(nx,ny)]=str(nlat)+'_'+str(nlon) 
    sdn[(0,0)]=waycodes[0]
    sdn[(0,Ny)]=waycodes[1]
    sdn[(Nx,Ny)]=waycodes[2]
    sdn[(Nx,0)]=waycodes[3]
    dico_edges.pop(waycodes[0]+'|'+waycodes[3],None)
    dico_edges.pop(waycodes[3]+'|'+waycodes[0],None)
    dico_edges.pop(waycodes[1]+'|'+waycodes[2],None)
    dico_edges.pop(waycodes[2]+'|'+waycodes[1],None)
    for ny in range(0,Ny+1):
        for nx in range(0,Nx):
            if ny==0 or ny==Ny:
                dico_edges[sdn[(nx,ny)]+'|'+sdn[(nx+1,ny)]]='patch'
            else:
                # fake but we want those to be traversed by the plague 
                # regional algo of Triangle4XP
                dico_edges[sdn[(nx,ny)]+'|'+sdn[(nx+1,ny)]]='orthogrid' 
    for ny in range(0,Ny):
        for nx in range(0,Nx+1):
            if nx==0 or nx==Nx:
                dico_edges[sdn[(nx,ny)]+'|'+sdn[(nx,ny+1)]]='patch'
            else:
                dico_edges[sdn[(nx,ny)]+'|'+sdn[(nx,ny+1)]]='orthogrid'
    eps=0.01
    testpt1=[(way[0]+way[2])/2.0+eps*(way[3]-way[1]),\
             (way[1]+way[3])/2.0-eps*(way[2]-way[0])]
    testpt2=[(way[0]+way[2])/2.0-eps*(way[3]-way[1]),\
             (way[1]+way[3])/2.0+eps*(way[2]-way[0])]
    if point_in_polygon(testpt1,way)==True:
        return [testpt1,(way[0]+way[6])/2.0,(way[1]+way[7])/2.0,\
                (way[2]+way[4])/2.0,(way[3]+way[5])/2.0]
    else:
        return [testpt2,(way[0]+way[6])/2.0,(way[1]+way[7])/2.0,\
                (way[2]+way[4])/2.0,(way[3]+way[5])/2.0]
#############################################################################

#############################################################################
def cut_edges_with_grid(lat0,lon0,dico_nodes,dico_edges,orthogrid=True):
    dico_edges_tmp={}
    xgrid=[]  # x coordinates of vertical grid lines
    ygrid=[]  # y coordinates of horizontal grid lines
    xcuts={}  # xcuts[y] will contain the x coordinates of the cut points on
              # the horiz line at y  
    ycuts={}  # ycuts[x] will contain the y coordinates of the cut points on
              # the vertical line at x
    
    # computation of the coordinates of the grid lines
    til_xul=ceil((lon0/180+1)*(2**(meshzl-1)))
    til_yul=ceil((1-log(tan((90+lat0+1)*pi/360))/pi)*(2**(meshzl-1)))
    til_xlr=floor(((lon0+1)/180+1)*(2**(meshzl-1)))
    til_ylr=floor((1-log(tan((90+lat0)*pi/360))/pi)*(2**(meshzl-1)))
    til_xul=ceil(til_xul/16)*16
    til_yul=ceil(til_yul/16)*16
    til_xlr=(til_xlr//16)*16
    til_ylr=(til_ylr//16)*16
    for til_x in range(int(til_xul),int(til_xlr+1),16):
        pos_x=(til_x/(2**(meshzl-1))-1)
        xgrid.append(pos_x*180-lon0+0.0)
    for til_y in range(int(til_yul),int(til_ylr+1),16):
        pos_y=(1-(til_y)/(2**(meshzl-1)))
        ygrid=[360/pi*atan(exp(pi*pos_y))-90-lat0+0.0]+ygrid
    if 0.0 not in xgrid:
        xgrid=[0.0]+xgrid
    if 1.0 not in xgrid:
        xgrid=xgrid+[1.0]
    if 0.0 not in ygrid:
        ygrid=[0.0]+ygrid
    if 1.0 not in ygrid:
        ygrid=ygrid+[1.0]
    # encoding nodes corresponding to grid points
    for x in xgrid:
        for y in ygrid:
            keep_node_xy(x,y,lat0,lon0,dico_nodes)
    # keeping track of the intersections of the vertical and horizontal lines
    # between themselves.
    for x in xgrid:
        ycuts[x]=ygrid
    for y in ygrid:
        xcuts[y]=xgrid
    # adding boundary points every 25m (roughly) to prevent tear between tiles
    for k in range(1,4000):
        keep_node_xy(0.0,k/4000.0,lat0,lon0,dico_nodes)
        keep_node_xy(1.0,k/4000.0,lat0,lon0,dico_nodes)
        keep_node_xy(k/4000.0,0.0,lat0,lon0,dico_nodes)
        keep_node_xy(k/4000.0,1.0,lat0,lon0,dico_nodes)
        xcuts[0.0]=xcuts[0.0]+[k/4000.0]
        xcuts[1.0]=xcuts[1.0]+[k/4000.0]
        ycuts[0.0]=ycuts[0.0]+[k/4000.0]
        ycuts[1.0]=ycuts[1.0]+[k/4000.0]
    # we compute the intersection of osm edges with horizontal tile boundaries 
    for edge in dico_edges:
        initpt=edge.split('|')[0]
        endpt=edge.split('|')[1]
        xi=xcoord(initpt,dico_nodes)
        yi=ycoord(initpt,dico_nodes)
        xf= xcoord(endpt,dico_nodes)
        yf= ycoord(endpt,dico_nodes)
        if ((yi<0 and 0<yf) or (yi>0 and 0>yf)):
            xcross= (0-yf)/(yi-yf)*xi+(yi-0)/(yi-yf)*xf
            if xcross>0 and xcross<1:
                xcuts[0.0]=xcuts[0.0]+[xcross]
            keep_node_xy(xcross,0.0,lat0,lon0,dico_nodes)
            if yi>0:
                keep_edge_str_tmp(initpt,strxy(xcross,0.0,lat0,lon0),\
                       dico_edges[edge],dico_edges_tmp)
            elif yf>0:
                keep_edge_str_tmp(strxy(xcross,0.0,lat0,lon0),\
                       endpt,dico_edges[edge],dico_edges_tmp)
        elif ((yi<1 and 1<yf) or (yi>1 and 1>yf)):
            xcross= (1-yf)/(yi-yf)*xi+(yi-1)/(yi-yf)*xf
            if xcross>0 and xcross<1:
                xcuts[1.0]=xcuts[1.0]+[xcross]
            keep_node_xy(xcross,1.0,lat0,lon0,dico_nodes)
            if yi<1:
                keep_edge_str_tmp(initpt,strxy(xcross,1.0,lat0,lon0),\
                       dico_edges[edge],dico_edges_tmp)
            elif yf<1:
                keep_edge_str_tmp(strxy(xcross,1.0,lat0,lon0),\
                       endpt,dico_edges[edge],dico_edges_tmp)
        elif ((yi==0) and (yf>0)):
            xcross=xi
            keep_node_xy(xcross,0.0,lat0,lon0,dico_nodes)
            xcuts[0.0]=xcuts[0.0]+[xcross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((yf==0) and (yi>0)):
            xcross=xf
            keep_node_xy(xcross,0.0,lat0,lon0,dico_nodes)
            xcuts[0.0]=xcuts[0.0]+[xcross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((yi==1) and (yf<1)):
            xcross=xi
            keep_node_xy(xcross,1.0,lat0,lon0,dico_nodes)
            xcuts[1.0]=xcuts[1.0]+[xcross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((yf==1) and (yi<1)):
            xcross=xf
            keep_node_xy(xcross,1.0,lat0,lon0,dico_nodes)
            xcuts[1.0]=xcuts[1.0]+[xcross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((yi==0) and (yf==0)):
            xcuts[0.0]=xcuts[0.0]+[xi,xf]
            keep_node_xy(xi,0.0,lat0,lon0,dico_nodes)
            keep_node_xy(xf,0.0,lat0,lon0,dico_nodes)
        elif ((yi==1) and (yf==1)):
            xcuts[1.0]=xcuts[1.0]+[xi,xf]
            keep_node_xy(xi,1.0,lat0,lon0,dico_nodes)
            keep_node_xy(xf,1.0,lat0,lon0,dico_nodes)
        elif (yi>0 and yi<1) and (yf>0 and yf<1): 
            dico_edges_tmp[edge]=dico_edges[edge]
    dico_edges=dico_edges_tmp
    dico_edges_tmp={}

    # we compute the intersection of (v-splitted) osm edges with vertical tile boundaries 
    for edge in dico_edges:
        initpt=edge.split('|')[0]
        endpt=edge.split('|')[1]
        xi=xcoord(initpt,dico_nodes)
        yi=ycoord(initpt,dico_nodes)
        xf= xcoord(endpt,dico_nodes)
        yf= ycoord(endpt,dico_nodes)
        if ((xi<0 and 0<xf) or (xi>0 and 0>xf)):
            ycross= (0-xf)/(xi-xf)*yi+(xi-0)/(xi-xf)*yf
            if ycross>0 and ycross<1:
                ycuts[0.0]=ycuts[0.0]+[ycross]
            keep_node_xy(0.0,ycross,lat0,lon0,dico_nodes)
            if xi>0:
                keep_edge_str_tmp(initpt,strxy(0.0,ycross,lat0,lon0),dico_edges[edge],\
                   dico_edges_tmp)
            elif xf>0:
                keep_edge_str_tmp(strxy(0.0,ycross,lat0,lon0),endpt,dico_edges[edge],\
                   dico_edges_tmp)
        elif ((xi<1 and 1<xf) or (xi>1 and 1>xf)):
            ycross= (1-xf)/(xi-xf)*yi+(xi-1)/(xi-xf)*yf
            if ycross>0 and ycross<1:
                ycuts[1.0]=ycuts[1.0]+[ycross]
            keep_node_xy(1.0,ycross,lat0,lon0,dico_nodes)
            if xi<1:
                keep_edge_str_tmp(initpt,strxy(1.0,ycross,lat0,lon0),dico_edges[edge],\
                   dico_edges_tmp)
            elif xf<1:
                keep_edge_str_tmp(strxy(1.0,ycross,lat0,lon0),endpt,dico_edges[edge],\
                   dico_edges_tmp)
        elif ((xi==0) and (xf>0)):
            ycross=yi
            keep_node_xy(0.0,ycross,lat0,lon0,dico_nodes)
            ycuts[0.0]=ycuts[0.0]+[ycross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((xf==0) and (xi>0)):
            ycross=yf
            keep_node_xy(0.0,ycross,lat0,lon0,dico_nodes)
            ycuts[0.0]=ycuts[0.0]+[ycross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((xi==1) and (xf<1)):
            ycross=yi
            keep_node_xy(1.0,ycross,lat0,lon0,dico_nodes)
            ycuts[1.0]=ycuts[1.0]+[ycross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((xf==1) and (xi<1)):
            ycross=yf
            keep_node_xy(1.0,ycross,lat0,lon0,dico_nodes)
            ycuts[1.0]=ycuts[1.0]+[ycross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((xi==0) and (xf==0)):
            ycuts[0.0]=ycuts[0.0]+[yi,yf]
            keep_node_xy(0.0,yi,lat0,lon0,dico_nodes)
            keep_node_xy(0.0,yf,lat0,lon0,dico_nodes)
        elif ((xi==1) and (xf==1)):
            ycuts[1.0]=ycuts[1.0]+[yi,yf]
            keep_node_xy(1.0,yi,lat0,lon0,dico_nodes)
            keep_node_xy(1.0,yf,lat0,lon0,dico_nodes)
        elif (xi>0 and xi<1) and (xf>0 and xf<1): 
            dico_edges_tmp[edge]=dico_edges[edge]
    dico_edges=dico_edges_tmp
    dico_edges_tmp={}
    
    
    # we compute the intersection of osm edges with inner horizontal grid lines 
    for edge in dico_edges:
        initpt=edge.split('|')[0]
        endpt=edge.split('|')[1]
        xi=xcoord(initpt,dico_nodes)
        yi=ycoord(initpt,dico_nodes)
        xf= xcoord(endpt,dico_nodes)
        yf= ycoord(endpt,dico_nodes)
        til_yi=floor((1-log(tan((90+lat0+yi)*pi/360))/pi)*(2**(meshzl-1)))
        til_yf=floor((1-log(tan((90+lat0+yf)*pi/360))/pi)*(2**(meshzl-1)))
        til_yi=(til_yi//16)*16
        til_yf=(til_yf//16)*16
        if til_yi != til_yf:
            #if abs(til_yi-til_yf) != 16:
               #print("arête coupant plusieurs lignes horizontales de la grilles : \n")
               #print(str(abs(til_yi-til_yf))+"\n")
            til_y0=max(til_yi,til_yf)
            y0=360/pi*atan(exp(pi*(1-(til_y0)/(2**(meshzl-1)))))-90-lat0
            xcross= (y0-yf)/(yi-yf)*xi+(yi-y0)/(yi-yf)*xf
            xcuts[y0]=xcuts[y0]+[xcross]
            keep_node_xy(xcross,y0,lat0,lon0,dico_nodes)
            keep_edge_str_tmp(initpt,strxy(xcross,y0,lat0,lon0),\
                   dico_edges[edge],dico_edges_tmp)
            keep_edge_str_tmp(strxy(xcross,y0,lat0,lon0),\
                   endpt,dico_edges[edge],dico_edges_tmp)
        else:
            dico_edges_tmp[edge]=dico_edges[edge]
      
    dico_edges=dico_edges_tmp
    dico_edges_tmp={}

    # then the intersection of osm edges with inner vertical grid lines 
    for edge in dico_edges:
        initpt=edge.split('|')[0]
        endpt=edge.split('|')[1]
        xi=xcoord(initpt,dico_nodes)
        yi=ycoord(initpt,dico_nodes)
        xf= xcoord(endpt,dico_nodes)
        yf= ycoord(endpt,dico_nodes)
        til_xi=floor(((lon0+xi)/180+1)*(2**(meshzl-1)))
        til_xf=floor(((lon0+xf)/180+1)*(2**(meshzl-1)))
        til_xi=(til_xi//16)*16
        til_xf=(til_xf//16)*16
        if til_xi != til_xf:
            #if abs(til_xi-til_xf) != 16:
                #print("arête coupant plusieurs lignes verticales de la grilles\n")
                #print(str(xi)+' '+str(yi)+' '+str(xf)+' '+str(yf)+"\n")
            til_x0=max(til_xi,til_xf)
            x0=(til_x0/(2**(meshzl-1))-1)*180-lon0
            ycross= (x0-xf)/(xi-xf)*yi+(xi-x0)/(xi-xf)*yf
            ycuts[x0]=ycuts[x0]+[ycross]
            keep_node_xy(x0,ycross,lat0,lon0,dico_nodes)
            keep_edge_str_tmp(initpt,strxy(x0,ycross,lat0,lon0),dico_edges[edge],\
                   dico_edges_tmp)
            keep_edge_str_tmp(strxy(x0,ycross,lat0,lon0),endpt,dico_edges[edge],\
                   dico_edges_tmp)
        else:
            dico_edges_tmp[edge]=dico_edges[edge]
    
    # finally we include edges that are formed by cutted grid lines        
    for y in xcuts:
        xcuts[y].sort()
        for k in range(0,len(xcuts[y])-1):
            dico_edges_tmp[strxy(xcuts[y][k],y,lat0,lon0)+'|'+\
                      strxy(xcuts[y][k+1],y,lat0,lon0)]='orthogrid'
    for x in ycuts:
        ycuts[x].sort()
        for k in range(0,len(ycuts[x])-1):
            dico_edges_tmp[strxy(x,ycuts[x][k],lat0,lon0)+'|'+\
                      strxy(x,ycuts[x][k+1],lat0,lon0)]='orthogrid'
    return dico_edges_tmp
#############################################################################



#############################################################################
# Petite routine bien utile : comment calculer rapidement l'aire d'un 
# polygone dont on dispose de la liste des sommets.  Le signe donne le sens
# de parcours horaire ou anti-horaire.
#############################################################################
def area(way):
   area=0
   x1=float(way[0][1])
   y1=float(way[0][0])
   for node in way[1:]:
       x2=float(node[1])
       y2=float(node[0])
       area+=(x2-x1)*(y2+y1)
       x1=x2
       y1=y2
   return area/2 
#############################################################################

#############################################################################
# Openstreetmap donne tous les objets qui intersectent la tuile, pour les
# objets de type 'rel' on peut virer les boucles fermées qui sont entièrement
# hors tuile (sinon par exemple pour lat=45 lon=5 on récupère le Rhônes 
# jusqu'à son embouchure !
#############################################################################
def touches_region(way,lat0,lat1,lon0,lon1):
    for node in way:
       if float(node[0])>=lat0 and float(node[0])<=lat1\
         and float(node[1])>=lon0 and float(node[1])<=lon1:
           return True
    return False
#############################################################################

#############################################################################
# Comment planter une petite graine qui de proche en proche découvrira tous
# les triangles en eau (en se baladant sans pouvoir traverser les arêtes du
# fichier .poly).
#############################################################################
def pick_point(way,side,lat0,lon0):
   if side=='left':
       sign=1
   elif side=='right':
       sign=-1
   dmin =0.00001 
   l=0
   ptin=False
   i=0
   while (l<dmin) or (ptin==False):
       if len(way)==i+1:
           break
       x1=float(way[i][1])
       y1=float(way[i][0])
       x2=float(way[i+1][1])
       y2=float(way[i+1][0])
       l=sqrt((x2-x1)**2+(y2-y1)**2)
       ptin=False
       if ((x2>lon0) and (x2<lon0+1) and (y2>lat0) and (y2<lat0+1)) and\
          ((x1>lon0) and (x1<lon0+1) and (y1>lat0) and (y1<lat0+1)):
           ptin=True
       i+=1
   if ptin==True:
       dperp=0.000001
       x=0.5*x1+0.5*x2+(y1-y2)/l*dperp*sign
       y=0.5*y1+0.5*y2+(x2-x1)/l*dperp*sign
       return [x,y]
   i=0
   ptin=False
   while (l<dmin) or (ptin==False):
       if len(way)==i+1:
           # This should never happen, we send it to hell
           return [1000,1000]
       x1=float(way[i][1])
       y1=float(way[i][0])
       x2=float(way[i+1][1])
       y2=float(way[i+1][0])
       l=sqrt((x2-x1)**2+(y2-y1)**2)
       ptin=False
       if ((x2>lon0) and (x2<lon0+1) and (y2>lat0) and (y2<lat0+1)):
           ptin=True
           ptend=2
       if ((x1>lon0) and (x1<lon0+1) and (y1>lat0) and (y1<lat0+1)):
           ptin=True
           ptend=1
       i+=1
   dperp=0.0000001
   if ptend==1:
       x=0.99*x1+0.01*x2+(y1-y2)/l*dperp*sign
       y=0.99*y1+0.01*y2+(x2-x1)/l*dperp*sign
   else:
       x=0.99*x2+0.01*x1+(y1-y2)/l*dperp*sign
       y=0.99*y2+0.01*y1+(x2-x1)/l*dperp*sign
   return [x,y]
#############################################################################

#############################################################################
def pick_point_check(way,side,lat0,lon0):
   if side=='left':
       sign=1
   elif side=='right':
       sign=-1
   dmin =0.00001 
   l=0
   ptin=False
   i=0
   while (l<dmin) or (ptin==False):
       if len(way)==i+1:
           break
       x1=float(way[i][1])
       y1=float(way[i][0])
       x2=float(way[i+1][1])
       y2=float(way[i+1][0])
       l=sqrt((x2-x1)**2+(y2-y1)**2)
       ptin=False
       if ((x2>lon0) and (x2<lon0+1) and (y2>lat0) and (y2<lat0+1)) and\
          ((x1>lon0) and (x1<lon0+1) and (y1>lat0) and (y1<lat0+1)):
           ptin=True
       i+=1
   if ptin==True:
       dperp=0.000001
       x=0.5*x1+0.5*x2+(y1-y2)/l*dperp*sign
       y=0.5*y1+0.5*y2+(x2-x1)/l*dperp*sign
       polygon=[]
       for node in way:
         polygon+=[float(node[1]),float(node[0])]
       if point_in_polygon([x,y],polygon):
         return [x,y]
       else:
         pass  
         #print("Wrong pick 1 !!!!!!!!!!!!!!!")  
         #print(polygon)
         #return [1000,1000]
   i=0
   ptin=False
   while (l<dmin) or (ptin==False):
       if len(way)==i+1:
           # This should never happen, we send it to hell
           return [1000,1000]
       x1=float(way[i][1])
       y1=float(way[i][0])
       x2=float(way[i+1][1])
       y2=float(way[i+1][0])
       l=sqrt((x2-x1)**2+(y2-y1)**2)
       ptin=False
       if ((x2>lon0) and (x2<lon0+1) and (y2>lat0) and (y2<lat0+1)):
           ptin=True
           ptend=2
       if ((x1>lon0) and (x1<lon0+1) and (y1>lat0) and (y1<lat0+1)):
           ptin=True
           ptend=1
       i+=1
   dperp=0.0000001
   if ptend==1:
       x=0.99*x1+0.01*x2+(y1-y2)/l*dperp*sign
       y=0.99*y1+0.01*y2+(x2-x1)/l*dperp*sign
   else:
       x=0.99*x2+0.01*x1+(y1-y2)/l*dperp*sign
       y=0.99*y2+0.01*y1+(x2-x1)/l*dperp*sign
   polygon=[]
   for node in way:
     polygon+=[float(node[1]),float(node[0])]
   if point_in_polygon([x,y],polygon):
    #print("Good pick !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!") 
    return [x,y]
   else:
    #print("Wrong pick 2 !!!!!!!!!!!!!!!!")  
    return [1000,1000]
#############################################################################
   

#############################################################################
def pick_points_safe(way,side,lat0,lon0,check=False):
   if side=='left':
       sign=1
   elif side=='right':
       sign=-1
   dmin =0.00001 
   return_list=[]
   not_yet_edge_fully_in=True
   for i in range(0,len(way)-1):
       x1=float(way[i][1])
       y1=float(way[i][0])
       x2=float(way[i+1][1])
       y2=float(way[i+1][0])
       l=abs(x2-x1)+abs(y2-y1)
       if l<dmin:
          continue    
       x2in= (x2>lon0) and (x2<lon0+1) and (y2>lat0) and (y2<lat0+1) 
       x1in= (x1>lon0) and (x1<lon0+1) and (y1>lat0) and (y1<lat0+1)
       if x1in and x2in and  not_yet_edge_fully_in:
          not_yet_edge_fully_in=False
          dperp=0.000001
          x=0.5*x1+0.5*x2+(y1-y2)/l*dperp*sign
          y=0.5*y1+0.5*y2+(x2-x1)/l*dperp*sign   
          return_list.append([x,y])
       elif x1in and not x2in:
          dperp=0.0000001
          x=0.99*x1+0.01*x2+(y1-y2)/l*dperp*sign
          y=0.99*y1+0.01*y2+(x2-x1)/l*dperp*sign
          return_list.append([x,y])
       elif x2in and not x1in:
          dperp=0.0000001
          x=0.99*x2+0.01*x1+(y1-y2)/l*dperp*sign
          y=0.99*y2+0.01*y1+(x2-x1)/l*dperp*sign
          return_list.append([x,y])
   if return_list==[]:
       return [[1000,1000]]
   if check:
       polygon=[]
       checked_return_list=[]
       for node in way:
           polygon+=[float(node[1]),float(node[0])]
       for point in return_list:
           if point_in_polygon(point,polygon):
               checked_return_list.append(point)
           else:
               checked_return_list.append([1000,1000])
       return checked_return_list        
   else:
       return return_list
#############################################################################





##############################################################################
# La construction des noms des fichiers d'altitudes, sera amené à changer 
# si de meilleures sources libres de DEM voient le jour. 
##############################################################################
def downloaded_dem_filename(lat,lon,source):
    if source=='SRTMv3_1(void filled)':
        if (lat >= 0):
            hemisphere='N'
        else:
            hemisphere='S'
        if (lon >= 0):
            greenwichside='E'
        else:
            greenwichside='W'
        filename="SRTMv3_1_"+hemisphere+'{:.0f}'.format(abs(lat)).zfill(2)+\
                greenwichside+'{:.0f}'.format(abs(lon)).zfill(3)+'.tif'
    if source=='SRTMv3_3(void filled)':
        if (lat >= 0):
            hemisphere='N'
        else:
            hemisphere='S'
        if (lon >= 0):
            greenwichside='E'
        else:
            greenwichside='W'
        filename="SRTMv3_3_"+hemisphere+'{:.0f}'.format(abs(lat)).zfill(2)+\
                greenwichside+'{:.0f}'.format(abs(lon)).zfill(3)+'.tif'
    elif source=='de_Ferranti':
        if (lat >= 0):
            hemisphere='N'
        else:
            hemisphere='S'
        if (lon >= 0):
            greenwichside='E'
        else:
            greenwichside='W'
        filename=hemisphere+'{:.0f}'.format(abs(lat)).zfill(2)+\
                greenwichside+'{:.0f}'.format(abs(lon)).zfill(3)+\
                '.hgt'
    elif source=='FR':
        filename='' # for future use maybe
    return Ortho4XP_dir+"/Elevation_data/"+filename
##############################################################################


##############################################################################
#  Chargement en mémoire des DEM. Si aucun fichier spécifié de Ferranti a la 
#   priorité sur SRTM là où   il est disponible.
##############################################################################
def load_altitude_matrix(lat,lon,filename='None'):
    filename_srtm1=downloaded_dem_filename(lat,lon,'SRTMv3_1(void filled)')
    filename_srtm3=downloaded_dem_filename(lat,lon,'SRTMv3_3(void filled)')
    filename_viewfinderpanorama=downloaded_dem_filename(lat,lon,'de_Ferranti')
    if filename=='None':
        if os.path.isfile(filename_viewfinderpanorama):
            filename=filename_viewfinderpanorama
        elif os.path.isfile(filename_srtm1):
            filename=filename_srtm1
        elif os.path.isfile(filename_srtm3):
            filename=filename_srtm3
        else:
            print("   No elevation file found, I download it from viewfinderpanorama (J. de Ferranti)")
            deferranti_nbr=str(31+lon//6)
            alphabet=list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            deferranti_letter=alphabet[lat//4] if lat>=0 else alphabet[(-1-lat)//4]
            if lat<0:
                deferranti_letter='S'+deferranti_letter
            s=requests.Session()
            dem_download_ok = False
            tentative=0
            while dem_download_ok != True and tentative<10:
                url="http://viewfinderpanoramas.org/dem3/"+deferranti_letter+deferranti_nbr+".zip"
                r=s.get(url)
                if ('Response [20' in str(r)):
                    print("   Done. The zip archive will now be extracted in the Elevation_data dir.") 
                    dem_download_ok=True
                else:
                    tentative+=1 
                    print("      Viewfinderpanorama server was busy, new tentative...")
                    time.sleep(1)
            if tentative==10:
                return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
            zipfile=open(Ortho4XP_dir+dir_sep+"tmp"+dir_sep+deferranti_letter+deferranti_nbr+".zip",'wb')
            zipfile.write(r.content)
            zipfile.close()
            os.system(unzip_cmd+' e -y -o'+Ortho4XP_dir+dir_sep+'Elevation_data'+' "'+\
              Ortho4XP_dir+dir_sep+'tmp'+dir_sep+deferranti_letter+deferranti_nbr+'.zip"')
            os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+deferranti_letter+deferranti_nbr+'.zip')
            filename=filename_viewfinderpanorama
            #usage('dem_files',do_i_quit=False) 
            #return 'error'
    if ('.hgt') in filename or ('.HGT' in filename):
        try:
            ndem=int(round(sqrt(os.path.getsize(filename)/2)))
            f = open(filename, 'rb')
            format = 'h'
            alt = array.array(format)
            alt.fromfile(f,ndem*ndem)
            f.close()
        except:
            usage('dem_files',do_i_quit=False) 
            return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
        alt.byteswap()
        alt=numpy.asarray(alt,dtype=numpy.float32).reshape((ndem,ndem)) 
    elif ('.tif' in filename) or ('.TIF' in filename):
        if gdal_loaded == True:
            try:
                ds=gdal.Open(filename)
                alt=numpy.float32(ds.GetRasterBand(1).ReadAsArray())
                ndem=ds.RasterXSize
            except:
                usage('dem_files',do_i_quit=False) 
                return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
        else:
            try:
                # geotiff file do not seem to be easily treated by PIL,
                # smashing them through convert is a weird workaround
                # since it removes some of the tags layer, but it works.     
                os.system(convert_cmd+' "'+filename+'" "'+filename +'" '+\
                        devnull_rdir)
                im=Image.open(filename)
                alt=numpy.float32(im)
                alt=alt-65536*(alt>10000)
                if alt.shape[0]==alt.shape[1]:
                    ndem=alt.shape[0]
                else:
                    usage('dem_files',do_i_quit=False) 
                    return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
            except:
                usage('dem_files',do_i_quit=False) 
                return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
    else:
        usage('dem_files',do_i_quit=False) 
        return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
    if alt.min()==-32768:
        print("")
        print("WARNING : The elevation file "+filename+" has some 'no data' zones, ")
        print("          I am filling the holes using a nearest neighbour approach.") 
        is_filled=False
        step=0
        while not is_filled:
            step+=1
            alt10=numpy.roll(alt,1,axis=0)
            alt10[0]=alt[0]
            alt20=numpy.roll(alt,-1,axis=0)
            alt20[-1]=alt[-1]
            alt01=numpy.roll(alt,1,axis=1)
            alt01[:,0]=alt[:,0]
            alt02=numpy.roll(alt,-1,axis=1)
            alt02[:,-1]=alt[:,-1]
            atemp=numpy.maximum(alt10,alt20)
            atemp=numpy.maximum(atemp,alt01)
            atemp=numpy.maximum(atemp,alt02)
            alt=alt+(32768+atemp)*(alt==-32768)
            if alt.min()>-32768:
                is_filled=True
            if step>100:
                print("The hole seems to big to be true... or the no data sign is not the one expected, I quit.")
                break
        print("          Done.\n") 
    return [alt,ndem]
##############################################################################
 

##############################################################################
# Altitude obtenue par interpolation pour les points hors de la grille du
# fichier DEM.
##############################################################################
def altitude(x,y,alt_dem,ndem):
    N=ndem-1
    if x<0:
        x=0
    if x>1:
        x=1
    if y<0:
        y=0
    if y>1:
        y=1
    px=x*N
    py=y*N
    nx=int(px)
    ny=int(py)
    rx=px-nx
    ry=py-ny
    if rx!=0 and ry!=0 and rx>=ry:
        z=(1-rx)*alt_dem[N-ny][nx]+\
           ry*alt_dem[N-ny-1][nx+1]+(rx-ry)*alt_dem[N-ny][nx+1]
    elif rx!=0 and ry!=0:
        z=(1-ry)*alt_dem[N-ny][nx]+\
          rx*alt_dem[N-ny-1][nx+1]+(ry-rx)*alt_dem[N-ny-1][nx]
    elif rx==0 and ry!=0:
        z=(1-ry)*alt_dem[N-ny][nx]+ry*alt_dem[N-ny-1][nx]
    elif ry==0 and rx!=0:
        z=(1-rx)*alt_dem[N-ny][nx]+rx*alt_dem[N-ny][nx+1]
    else:
        z=alt_dem[N-ny][nx]
    return z
##############################################################################


##############################################################################
#  Construction des altitudes des points du maillage, et mise à zéro des
#  triangles de mer (pour éviter les effets indésirables des erreurs des
#  fichiers DEM sur le litoral lorsque celui-ci est accidenté). 
##############################################################################
def build_3D_vertex_array(lat,lon,alt_dem,ndem,build_dir):
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    node_filename = build_dir+dir_sep+'Data'+strlat+strlon+'.1.node'
    ele_filename  = build_dir+dir_sep+'Data'+strlat+strlon+'.1.ele'
    apt_filename  = build_dir+dir_sep+'Data'+strlat+strlon+'.apt'
    f_node = open(node_filename,'r')
    f_ele  = open(ele_filename,'r')
    f_apt  = open(apt_filename,'r')
    nbr_pt=int(f_node.readline().split()[0])
    vertices=numpy.zeros(5*nbr_pt)
    print("-> Loading of the mesh computed by Triangle4XP.")
    for i in range(0,nbr_pt):
        coordlist=f_node.readline().split()
        vertices[5*i]=float(coordlist[1])+lon
        vertices[5*i+1]=float(coordlist[2])+lat
        vertices[5*i+2]=float(coordlist[3])
        vertices[5*i+3]=float(coordlist[4])
        vertices[5*i+4]=float(coordlist[5])
    f_node.close()
    # Now we modify the altitude we got from the DEM in certain 
    # circumstances, because we want flat water, flat (or correctly sloped
    # airports, etc. One pass would be sufficient in principle but I 
    # prefer one pass per triangle type, to have better control in
    # case of nodes belonging different triangle types.
    print("-> Flattening of oceans and seas, smoothing of lakes and rivers (1st pass)")
    # Here we put all nodes belonging to at least one sea triangle
    # i.e. (with ele marker = 2) to zero altitude. 
    f_ele=open(ele_filename,'r')
    nbr_tri=int(f_ele.readline().split()[0])
    regiontag=True
    for i in range(0,nbr_tri):
        idx=f_ele.readline().split()
        v1=(int(idx[1])-1)
        v2=(int(idx[2])-1)
        v3=(int(idx[3])-1)
        if idx[4] == dico_tri_markers['sea']:
            vertices[5*v1+2]=0
            vertices[5*v2+2]=0
            vertices[5*v3+2]=0
        elif idx[4] in [dico_tri_markers['water'],\
                dico_tri_markers['sea_equiv']]:
            zmean=(vertices[5*v1+2]+vertices[5*v2+2]+vertices[5*v3+2])/3
            vertices[5*v1+2]=zmean
            vertices[5*v2+2]=zmean
            vertices[5*v3+2]=zmean
    print("-> Flattening of airports and treatment of patches, smoothing (2nd pass).")
    f_ele.seek(0)
    f_ele.readline()
    dico_alt_ap={}
    for i in range(0,nbr_tri):
        idx=f_ele.readline().split()
        v1=(int(idx[1])-1)
        v2=(int(idx[2])-1)
        v3=(int(idx[3])-1)
        if idx[4] in [dico_tri_markers['water'],\
                    dico_tri_markers['sea_equiv']]:
            if tile_has_water_airport!=True: # the parallel process does not otherwise ensure that airports are flat
                zmean=(vertices[5*v1+2]+vertices[5*v2+2]+vertices[5*v3+2])/3
                vertices[5*v1+2]=zmean
                vertices[5*v2+2]=zmean
                vertices[5*v3+2]=zmean
        elif (100 <= int(idx[4])) and (int(idx[4])<1000):
            if idx[4] in dico_alt_ap:
                height=dico_alt_ap[idx[4]]
                vertices[5*v1+2]=height
                vertices[5*v2+2]=height
                vertices[5*v3+2]=height
                continue
            found=False
            f_apt.seek(0)
            while found!=True:
                tmplist=f_apt.readline()
                if tmplist=='':
                    print("Error processing the .apt file.")
                    sys.exit()
                if "Airport" in tmplist:
                    tmplist=tmplist.split()
                    if tmplist[1]==str(int(idx[4])):
                        nbr_nodes=int(tmplist[3])
                        found=True
            osm_height=f_apt.readline().split()[1]
            height=0
            apt_crosses_tile=False
            for k in range(0,nbr_nodes):
                tmplist=f_apt.readline().split()
                x=float(tmplist[1])-lon
                y=float(tmplist[0])-lat
                if (x<0 or x>1 or y<0 or y>1):
                    apt_crosses_tile=True
                height+=altitude(x,y,alt_dem,ndem)
            height=height/nbr_nodes
            if apt_crosses_tile==True and osm_height != 'unknown':
                # (crude) ele tag is max elevation, not mean elevation
                height=float(osm_height)-8  
            vertices[5*v1+2]=height
            vertices[5*v2+2]=height
            vertices[5*v3+2]=height
            dico_alt_ap[idx[4]]=height
        elif int(idx[4])>=1000 and int(idx[4])<10000:
            if idx[4] in dico_alt_ap:
                height=dico_alt_ap[idx[4]]
                vertices[5*v1+2]=height
                vertices[5*v2+2]=height
                vertices[5*v3+2]=height
                continue
            found=False
            f_apt.seek(0)
            while found!=True:
                tmplist=f_apt.readline()
                if tmplist=='':
                    print("Error processing the .apt file.")
                    sys.exit()
                if "Flat_patch" in tmplist:
                    tmplist=tmplist.split()
                    if tmplist[1]==str(int(idx[4])):
                        nbr_nodes=int(tmplist[3])
                        found=True
            patch_height=f_apt.readline().split()[1]
            if patch_height=='mean':
                height=0
                for k in range(0,nbr_nodes):
                    tmplist=f_apt.readline().split()
                    x=float(tmplist[1])-lon
                    y=float(tmplist[0])-lat
                    height+=altitude(x,y,alt_dem,ndem)
                height=height/nbr_nodes
            else:
                height=float(patch_height)
            vertices[5*v1+2]=height
            vertices[5*v2+2]=height
            vertices[5*v3+2]=height
            dico_alt_ap[idx[4]]=height
        elif 10000 <= int(idx[4]):
            if idx[4] in dico_alt_ap:
                tmplist=dico_alt_ap[idx[4]]
            else:
                found=False
                f_apt.seek(0)
                while found!=True:
                    tmplist=f_apt.readline()
                    if tmplist=='':
                        print("Error processing the .apt file.")
                        sys.exit()
                    if "Sloped_patch" in tmplist:
                        tmplist=tmplist.split()
                        if tmplist[1]==str(int(idx[4])):
                            found=True
                            dico_alt_ap[idx[4]]=tmplist
            xi=float(tmplist[3])
            yi=float(tmplist[4])
            xf=float(tmplist[5])
            yf=float(tmplist[6])
            zi=float(tmplist[7])
            zf=float(tmplist[8])
            x1=vertices[5*v1]-lon
            y1=vertices[5*v1+1]-lat
            x2=vertices[5*v2]-lon
            y2=vertices[5*v2+1]-lat
            x3=vertices[5*v3]-lon
            y3=vertices[5*v3+1]-lat
            rat1=((x1-xi)*(xf-xi)+(y1-yi)*(yf-yi))/((xf-xi)**2+(yf-yi)**2)
            rat2=((x2-xi)*(xf-xi)+(y2-yi)*(yf-yi))/((xf-xi)**2+(yf-yi)**2)
            rat3=((x3-xi)*(xf-xi)+(y3-yi)*(yf-yi))/((xf-xi)**2+(yf-yi)**2)
            steepness=float(tmplist[10])
            if tmplist[9]=='atanh':
                vertices[5*v1+2]=(zi+zf)/2+(zf-zi)/2*atan(steepness*(rat1-0.5))/\
                        atan(steepness/2)
                vertices[5*v2+2]=(zi+zf)/2+(zf-zi)/2*atan(steepness*(rat2-0.5))/\
                        atan(steepness/2)
                vertices[5*v3+2]=(zi+zf)/2+(zf-zi)/2*atan(steepness*(rat3-0.5))/\
                        atan(steepness/2)
            elif tmplist[9]=='spline':
                vertices[5*v1+2]=zi+3*(zf-zi)*rat1**2-2*(zf-zi)*rat1**3
                vertices[5*v2+2]=zi+3*(zf-zi)*rat2**2-2*(zf-zi)*rat2**3
                vertices[5*v3+2]=zi+3*(zf-zi)*rat3**2-2*(zf-zi)*rat3**3
            elif tmplist[9]=='parabolic':
                zi,zf=zf,zi
                rat1,rat2,rat3=1-rat1,1-rat2,1-rat3
                vertices[5*v1+2]=zi+(zf-zi)*rat1**2
                vertices[5*v2+2]=zi+(zf-zi)*rat2**2
                vertices[5*v3+2]=zi+(zf-zi)*rat3**2
            else:
                print("One of the patch profiles is unknown to me, I use a plane one instead.")
                vertices[5*v1+2]=zi+rat1*(zf-zi)
                vertices[5*v2+2]=zi+rat2*(zf-zi)
                vertices[5*v3+2]=zi+rat3*(zf-zi)
    if water_smoothing >= 3:
        print("   Smoothing of lakes and rivers (ultimate passes).")
        # Next, we average altitudes of triangles of fresh water type.  
        # Of course one such operation slightly breaks other ones, but there is 
        # not a perfect solution to this because the altitude close to the source
        # of a river differs from its altitude at is very end, water is not
        # flat all way long.
        for j in range(0,water_smoothing-2):   
            f_ele.seek(0)
            f_ele.readline()
            for i in range(0,nbr_tri):
                idx=f_ele.readline().split()
                v1=(int(idx[1])-1)
                v2=(int(idx[2])-1)
                v3=(int(idx[3])-1)
                if idx[4] in [dico_tri_markers['water'],\
                    dico_tri_markers['sea_equiv']]:
                    zmean=(vertices[5*v1+2]+vertices[5*v2+2]+vertices[5*v3+2])/3
                    vertices[5*v1+2]=zmean
                    vertices[5*v2+2]=zmean
                    vertices[5*v3+2]=zmean
    f_apt.close()
    f_ele.close()
    return vertices
##############################################################################

##############################################################################
# Write of the mesh file based on .1.ele, .1.node and vertices
##############################################################################
def build_mesh_file(lat,lon,vertices,mesh_filename,build_dir):
    print("-> Writing of the final mesh to the file "+mesh_filename)
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    ele_filename  = build_dir+dir_sep+'Data'+strlat+strlon+'.1.ele'
    f_ele  = open(ele_filename,'r')
    nbr_vert=len(vertices)//5
    nbr_tri=int(f_ele.readline().split()[0])
    f=open(mesh_filename,"w")
    f.write("MeshVersionFormatted 1\n")
    f.write("Dimension 3\n\n")
    f.write("Vertices\n")
    f.write(str(nbr_vert)+"\n")
    for i in range(0,nbr_vert):
        f.write('{:.9f}'.format(vertices[5*i])+" "+\
                '{:.9f}'.format(vertices[5*i+1])+" "+\
                '{:.9f}'.format(vertices[5*i+2]/100000)+" 0\n") 
    f.write("\n")
    f.write("Normals\n")
    f.write(str(nbr_vert)+"\n")
    for i in range(0,nbr_vert):
        f.write('{:.9f}'.format(vertices[5*i+3])+" "+\
                '{:.9f}'.format(vertices[5*i+4])+"\n")
    f.write("\n")
    f.write("Triangles\n")
    f.write(str(nbr_tri)+"\n")
    for i in range(0,nbr_tri):
        f.write(' '.join(f_ele.readline().split()[1:])+"\n")
    f_ele.close()
    f.close()
    return
##############################################################################

##############################################################################
def build_mesh(lat,lon,build_dir):
    t2=time.time()
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    alt_filename  = build_dir+dir_sep+'Data'+strlat+strlon+'.alt'
    node_filename = build_dir+dir_sep+'Data'+strlat+strlon+'.1.node'
    ele_filename  = build_dir+dir_sep+'Data'+strlat+strlon+'.1.ele'
    poly_file     = build_dir+dir_sep+'Data'+strlat+strlon+'.poly'
    apt_filename  = build_dir+dir_sep+'Data'+strlat+strlon+'.apt'
    if os.path.isfile(apt_filename)!=True or os.path.isfile(poly_file)!=True:
        print("You must first build OSM data !")
        return
    mesh_filename = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
    print('-> Loading of elevation data.')
    try:
        if application.cdc.get()!=0:
            load_result=load_altitude_matrix(lat,lon,filename=application.cde.get())
        else:
            load_result=load_altitude_matrix(lat,lon)
    except:
        load_result=load_altitude_matrix(lat,lon)
    #if load_result=='error':
    #    print('\nFailure.')
    #    print('_____________________________________________________________'+\
    #        '____________________________________')
    #    return
    [alt_dem,ndem]=load_result
    alt_dem.tofile(alt_filename)
    print("-> Start of the mesh algorithm Triangle4XP :\n") 
    if no_small_angles==True:
        Tri_option = ' -pq'+str(smallest_angle)+'uAYPQ '
    else:
        Tri_option = ' -pAuYPQ '
    mesh_cmd=[Triangle4XP_cmd.strip(),Tri_option.strip(),str(ndem),str(curvature_tol),\
            str(hmax/100000),str(hmin/100000),alt_filename,poly_file]
    fingers_crossed=subprocess.Popen(mesh_cmd,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            print(line.decode("utf-8")[:-1])
    vertices=build_3D_vertex_array(lat,lon,alt_dem,ndem,build_dir)
    build_mesh_file(lat,lon,vertices,mesh_filename,build_dir)
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-t2))+\
              'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
    return
##############################################################################


##############################################################################
#                                                                            #
# IV : Toutes les méthodes à vocation géographique, essentiellement ce       #
#      qui concerne les changements de référentiel (WGS84 - Lambert - UTM)   #
#      ou la numérotation des vignettes (TMS - Quadkey).                     #
#      J'appelle "vignette" les images de 256x256 ou 512x512 pixels qui      #
#      contiennent des orthophotos et que l'on pourra télécharger à la       #
#      chaîne chez nos amis du fichier Carnet_d_adresses.py                  #
#                                                                            #
##############################################################################
##############################################################################
def wgs84_to_gtile(lat,lon,zoomlevel):                                          
    half_meridian=pi*6378137
    rat_x=lon/180           
    rat_y=log(tan((90+lat)*pi/360))/pi
    pix_x=round((rat_x+1)*(2**(zoomlevel+7)))
    pix_y=round((1-rat_y)*(2**(zoomlevel+7)))
    til_x=pix_x//256
    til_y=pix_y//256
    return [til_x,til_y]
##############################################################################

##############################################################################
def wgs84_to_pix(lat,lon,zoomlevel):                                          
    half_meridian=pi*6378137
    rat_x=lon/180           
    rat_y=log(tan((90+lat)*pi/360))/pi
    pix_x=round((rat_x+1)*(2**(zoomlevel+7)))
    pix_y=round((1-rat_y)*(2**(zoomlevel+7)))
    return [pix_x,pix_y]
##############################################################################

##############################################################################
def gtile_to_wgs84(til_x,til_y,zoomlevel):
    """
    Returns the latitude and longitude of the top left corner of the tile 
    (til_x,til_y) at zoom level zoomlevel, using Google's numbering of tiles 
    (i.e. origin on top left of the earth map)
    """
    rat_x=(til_x/(2**(zoomlevel-1))-1)
    rat_y=(1-til_y/(2**(zoomlevel-1)))
    lon=rat_x*180
    lat=360/pi*atan(exp(pi*rat_y))-90
    return [lat,lon]
##############################################################################

##############################################################################
def pix_to_wgs84(pix_x,pix_y,zoomlevel):
    rat_x=(pix_x/(2**(zoomlevel+7))-1)
    rat_y=(1-pix_y/(2**(zoomlevel+7)))
    lon=rat_x*180
    lat=360/pi*atan(exp(pi*rat_y))-90
    return [lat,lon]
##############################################################################

##############################################################################
def gtile_to_quadkey(til_x,til_y,zoomlevel):
    """
    Translates Google coding of tiles to Bing Quadkey coding. 
    """
    quadkey=""
    temp_x=til_x
    temp_y=til_y    
    for step in range(1,zoomlevel+1):
        size=2**(zoomlevel-step)
        a=temp_x//size
        b=temp_y//size
        temp_x=temp_x-a*size
        temp_y=temp_y-b*size
        quadkey=quadkey+str(a+2*b)
    return quadkey
##############################################################################


##############################################################################
#                                                                            #
# V  :  Une texture est un fichier image de 4096x4096 pixels, obtenu à       #
#       partir de 256 vignettes accolées en 16 lignes et 16 colonnes.        #
#       Ce sont elles qui seront chargées ensuite par X-Plane.               #
#       La section qui suit propose entre autres des méthodes pour           #
#       télécharger et créer ces textures, déterminer si un masque alpha     #
#       de bord de mer est nécessaire, écrire les fichiers .ter ou encore    #
#       associer un pixel à un point géographique, et inversément.           #
#                                                                            #
##############################################################################

##############################################################################
#  Comment appeler le bébé ?
##############################################################################
def filename_from_attributes(strlat,strlon,til_x_left,til_y_top,\
                             zoomlevel,website):
    file_dir=Ortho4XP_dir+dir_sep+"Orthophotos"+dir_sep+strlat+strlon+\
                    dir_sep+website+'_'+str(zoomlevel)+dir_sep
    #if website=='g2xpl_8':
    #    file_name='g2xpl_8_'+str(zoomlevel)+'_'+str(til_x_left)+'_'+\
    #            str(2**zoomlevel-8-til_y_top)
    #elif website=='g2xpl_16':
    #    file_name='g2xpl_16_'+str(zoomlevel)+'_'+str(til_x_left)+'_'+\
    #            str(2**zoomlevel-16-til_y_top)
    #else:
    file_name=str(til_y_top)+"_"+str(til_x_left)+"_"+website+str(zoomlevel)   
    file_ext=".jpg"
    return [file_dir,file_name,file_ext]
##############################################################################

##############################################################################
#  Y suis-je ? (dans le rectangle)
##############################################################################
def is_in_region(lat,lon,latmin,latmax,lonmin,lonmax):
    if (lat>=latmin and lat<=latmax and lon>=lonmin and lon<=lonmax):
        retval=True
    else:
        retval=False
    return retval
##############################################################################

##############################################################################
def wgs84_to_texture(lat,lon,zoomlevel,website):
    ratio_x=lon/180           
    ratio_y=log(tan((90+lat)*pi/360))/pi
    #if website=='g2xpl_8':
    #    mult=2**(zoomlevel-4)
    #    til_x=int((ratio_x+1)*mult)*8
    #    til_y=int((1-ratio_y)*mult)*8
    #else:
    mult=2**(zoomlevel-5)
    til_x=int((ratio_x+1)*mult)*16
    til_y=int((1-ratio_y)*mult)*16
    return [til_x,til_y]
##############################################################################

##############################################################################
# Cfr. le manuel de DSFTool (wiki.x-plane.com), ce sont les coordonnées à 
# l'intérieur d'une texture avec (0,0) en bas à gauche et (1,1) en haut à 
# droite.
##############################################################################
def st_coord(lat,lon,tex_x,tex_y,zoomlevel,website):                        
    """
    ST coordinates of a point in a texture
    """
    if website not in st_proj_coord_dict: # hence in epsg:4326
        ratio_x=lon/180           
        ratio_y=log(tan((90+lat)*pi/360))/pi
        mult=2**(zoomlevel-5)
        s=(ratio_x+1)*mult-(tex_x//16)
        t=1-((1-ratio_y)*mult-tex_y//16)
        s = s if s>=0 else 0
        s = s if s<=1 else 1
        t = t if t>=0 else 0
        t = t if t<=1 else 1
        return [s,t]
    else:
        [latmax,lonmin]=gtile_to_wgs84(tex_x,tex_y,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(tex_x+16,tex_y+16,zoomlevel)
        [ulx,uly]=pyproj.transform(epsg['4326'],epsg[st_proj_coord_dict[website]],lonmin,latmax)
        [urx,ury]=pyproj.transform(epsg['4326'],epsg[st_proj_coord_dict[website]],lonmax,latmax)
        [llx,lly]=pyproj.transform(epsg['4326'],epsg[st_proj_coord_dict[website]],lonmin,latmin)
        [lrx,lry]=pyproj.transform(epsg['4326'],epsg[st_proj_coord_dict[website]],lonmax,latmin)
        minx=min(ulx,llx)
        maxx=max(urx,lrx)
        miny=min(lly,lry)
        maxy=max(uly,ury)
        deltax=maxx-minx
        deltay=maxy-miny
        [x,y]=pyproj.transform(epsg['4326'],epsg[st_proj_coord_dict[website]],lon,lat)
        s=(x-minx)/deltax
        t=(y-miny)/deltay
        s = s if s>=0 else 0
        s = s if s<=1 else 1
        t = t if t>=0 else 0
        t = t if t<=1 else 1
        return [s,t]
    #elif website=='g2xpl_8':
    #    ratio_x=lon/180           
    #    ratio_y=log(tan((90+lat)*pi/360))/pi
    #    mult=2**(zoomlevel-4)
    #    s=(ratio_x+1)*mult-(tex_x//8)
    #    t=1-((1-ratio_y)*mult-tex_y//8)
    #    s = s if s>=0 else 0
    #    s = s if s<=1 else 1
    #    t = t if t>=0 else 0
    #    t = t if t<=1 else 1
    #    return [s,t]
##############################################################################

##############################################################################
def attribute_texture(lat1,lon1,lat2,lon2,lat3,lon3,ortho_list,tri_type):
    bary_lat=(lat1+lat2+lat3)/3
    bary_lon=(lon1+lon2+lon3)/3
    asked_for=False
    if tri_type in ['2','3']:
        if sea_texture_params!=[]:
            website=sea_texture_params[0]
            zoomlevel=sea_texture_params[1]
            return wgs84_to_texture(bary_lat,bary_lon,zoomlevel,website)+\
                [zoomlevel]+[website]
    for region in ortho_list:
        if point_in_polygon([bary_lat,bary_lon],region[0]):
            zoomlevel=int(region[1])
            website=str(region[2])
            asked_for=True
            break
    if asked_for==False:
        return 'None'
    else:
        return wgs84_to_texture(bary_lat,bary_lon,zoomlevel,website)+\
                [zoomlevel]+[website]
##############################################################################


##############################################################################
#  The master procedure to download pieces of what will become a 4K texture.
#  The process depend on the provider.
##############################################################################



def build_jpeg_ortho(strlat,strlon,til_x_left,til_y_top,zoomlevel,website):
    big_image=Image.new('RGB',(4096,4096)) 
    jobs=[]
    if website in px256_list:
        for til_y in range(til_y_top,til_y_top+16):
            fargs=[til_x_left,til_y_top,til_y,zoomlevel,website,big_image]
            connection_thread=threading.Thread(target=obtain_jpeg_row,\
                          args=fargs)
            jobs.append(connection_thread)
    elif website in wms2048_list:
        for monty in [0,1]:
            for montx in [0,1]:
                fargs=[til_x_left,til_y_top,zoomlevel,website,montx,monty,big_image]
                connection_thread=threading.Thread(target=obtain_wms_part,\
                        args=fargs)
                jobs.append(connection_thread)
    else:
        print("!!! The requested provider no longer seems to be activated in your address book !!!")
        return
    for j in jobs:
        j.start()
    for j in jobs:
        j.join()
    [file_dir,file_name,file_ext]=\
            filename_from_attributes(strlat,strlon,til_x_left,til_y_top,\
                                          zoomlevel,website)
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    big_image.save(file_dir+file_name+file_ext)
    return


def obtain_jpeg_row(til_x_left,til_y_top,til_y,zoomlevel,website,big_image):
    """
    Obtain 16 gtiles in a row, http transactions take time so better 
    stay in line for a few consecutive tiles. We shall thread these calls in 
    the next function.
    """
    s=requests.Session()
    for til_x in range(til_x_left,til_x_left+16):
        [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,website)
        successful_download=False
        while successful_download==False:
            try:
                r=s.get(url, headers=fake_headers,timeout=10)
                if 'image' in r.headers['Content-Type'] or check_tms_response==False: 
                    successful_download=True
                else:
                    if use_bing_for_non_existent_data==True:
                        [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,'BI')
                    else:
                        print("Presumably a missed cache or non existent data, will try again in 1sec...")
                        print("(Leave check_response unchecked if you want to bypass this)")
                        #print(r.headers)
                        #print(r)
                        #print(r.content)
                        time.sleep(0.1)
            except requests.exceptions.RequestException as e:   
                print(e)
                print("We will try again in 1sec...")
                try:
                    if application.red_flag.get()==1:
                        print("Download process interrupted.")
                        return
                except:
                    pass
                time.sleep(1)
        if ('Response [20' in str(r)):
            small_image=Image.open(io.BytesIO(r.content))
            big_image.paste(small_image,((til_x-til_x_left)*256,(til_y-til_y_top)*256))
        else:
            small_image=Image.open(Ortho4XP_dir+dir_sep+'Utils'+dir_sep+\
                      'white.jpg')
            big_image.paste(small_image,((til_x-til_x_left)*256,(til_y-til_y_top)*256))
    return
##############################################################################



##############################################################################
# Obtain a piece of texture from a wms 
##############################################################################
def obtain_wms_part(til_x_left,til_y_top,zoomlevel,website,montx,monty,big_image):
    til_x=til_x_left+montx*8
    til_y=til_y_top+monty*8
    [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,website)
    file_ext=".jpg" 
    successful_download=False
    tentatives=0
    while successful_download==False:
        s=requests.Session()
        try:
            r=s.get(url, headers=fake_headers,timeout=wms_timeout)
            if ('Response [20' in str(r)):
                if 'image' in r.headers['Content-Type']:
                    if len(r.content)>=tricky_provider_hack or tentatives>=5:
                        small_image=Image.open(io.BytesIO(r.content))
                        big_image.paste(small_image,(montx*2048,monty*2048))
                        successful_download=True
                    else:
                        tentatives+=1
                else:
                    print("server "+str(url[10])+" error, len(r.content)="+\
                          str(len(r.content))+", : retrying in 2 secs...")
                    try:
                        if application.red_flag.get()==1:
                            print("Download process interrupted.")
                            return
                    except:
                        pass
                    #print(r.content)
                    # let's try another random server...
                    [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,website)
                    time.sleep(2)
            else:
                print("Server said no data : ", r," , using white square instead")
                small_image=Image.open(Ortho4XP_dir+dir_sep+'Utils'+dir_sep+\
                      'white2048.jpg')
                big_image.paste(small_image,(montx*2048,monty*2048))
                successful_download=True
                successful_download=True
        except requests.exceptions.RequestException as e:    
            print(e)
            print("We will try again in 2sec...")
            # let's try another random server...
            try:
                if application.red_flag.get()==1:
                    print("Download process interrupted.")
                    return
            except:
                    pass
            [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,website)
            time.sleep(2)
    return
##############################################################################

###############################################################################
def build_texture_region(latmin,latmax,lonmin,lonmax,zoomlevel,website):
    #[til_xmin,til_ymin]=wgs84_to_texture(latmax,lonmin,zoomlevel,website)
    #[til_xmax,til_ymax]=wgs84_to_texture(latmin,lonmax,zoomlevel,website)
    #print("Number of tiles to download (at most) : "+\
    #       str(((til_ymax-til_ymin)/16+1)*((til_xmax-til_xmin)/16+1)))
    #for til_y_top in range(til_ymin,til_ymax+1,16):
    #    for til_x_left in range(til_xmin,til_xmax+1,16):
    #        build_texture('XXX','YYY',til_x_left,til_y_top,zoomlevel,website)
    return   
###############################################################################

###############################################################################
def create_tile_preview(latmin,lonmin,zoomlevel,website):
    strlat='{:+.0f}'.format(latmin).zfill(3)
    strlon='{:+.0f}'.format(lonmin).zfill(4)
    if not os.path.exists(Ortho4XP_dir+dir_sep+'Previews'):
        os.makedirs(Ortho4XP_dir+dir_sep+'Previews') 
    os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'Previews'+\
               dir_sep+'image-*.jpg '+devnull_rdir)
    filepreview=Ortho4XP_dir+dir_sep+'Previews'+dir_sep+strlat+\
                  strlon+"_"+website+str(zoomlevel)+".jpg"       
    if os.path.isfile(filepreview) != True:
        [til_x_min,til_y_min]=wgs84_to_gtile(latmin+1,lonmin,zoomlevel)
        [til_x_max,til_y_max]=wgs84_to_gtile(latmin,lonmin+1,zoomlevel)
        nx=til_x_max-til_x_min+1
        ny=til_y_max-til_y_min+1
        big_image=Image.new('RGB',(256*nx,256*ny))
        s=requests.Session()
        total_x=(til_x_max+1-til_x_min)
        for til_x in range(til_x_min,til_x_max+1):
            for til_y in range(til_y_min,til_y_max+1):
                successful_download=False
                while successful_download==False:
                    try:
                        [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,website)
                        r=s.get(url, headers=fake_headers)
                        successful_download=True
                    except:
                        #print("Connexion avortée par le serveur, nouvelle tentative dans 1sec")
                        time.sleep(0.01)
                if ('Response [20' in str(r)):
                    small_image=Image.open(io.BytesIO(r.content))
                    big_image.paste(small_image,((til_x-til_x_min)*256,(til_y-til_y_min)*256))
                else:
                    small_image=Image.open(Ortho4XP_dir+dir_sep+'Utils'+dir_sep+\
                      'white.jpg')
                    big_image.paste(small_image,((til_x-til_x_min)*256,(til_y-til_y_min)*256))
            #try:
            application.preview_window.progress_preview.set(int(100*(til_x+1-til_x_min)/total_x))
            #except:
            #    pass
        big_image.save(filepreview)
        return
##############################################################################

###############################################################################
def create_vignette(tilx0,tily0,tilx1,tily1,zoomlevel,website,vignette_name):
        big_image=Image.new('RGB',(tilx1-tilx0)*256,(tily1-tily0)*256)
        s=requests.Session()
        for til_x in range(tilx0,tilx1):
            for til_y in range(tily0,tily1):
                successful_download=False
                while successful_download==False:
                    try:
                        [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,website)
                        r=s.get(url, headers=fake_headers)
                        successful_download=True
                    except:
                        #print("Connexion avortée par le serveur, nouvelle tentative dans 1sec")
                        time.sleep(0.01)
                if ('Response [20' in str(r)):
                    small_image=Image.open(io.BytesIO(r.content))
                    big_image.paste(small_image,((til_x-tilx0)*256,(til_y-tily0)*256))
                else:
                    small_image=Image.open(Ortho4XP_dir+dir_sep+'Utils'+dir_sep+\
                      'white.jpg')
                    big_image.paste(small_image,((til_x-tilx0)*256,(til_y-tily0)*256))
        big_image.save(vignette_name)
        return
##############################################################################

###############################################################################
def create_vignettes(zoomlevel,website):
        nbr_pieces=2**(zoomlevel-3)
        for nx in range(0,nbr_pieces):
            for ny in range(0,nbr_pieces):
               vignette_name=Ortho4XP_dir+dir_sep+"Previews"+dir_sep+"Earth"+\
                  dir_sep+"Earth2_ZL"+str(zoomlevel)+"_"+str(nx)+'_'+str(ny)+'.jpg'
               tilx0=nx*8
               tily0=ny*8
               create_vignette(tilx0,tily0,tilx0+8,tily0+8,zoomlevel,website,vignette_name) 
        return
##############################################################################

##############################################################################
# Les fichiers .ter de X-Plane (ici la version pour les zones non immergées).
##############################################################################
def create_terrain_file(build_dir,file_name,til_x_left,til_y_top,zoomlevel,website):
    if not os.path.exists(build_dir+dir_sep+'terrain'):
        os.makedirs(build_dir+dir_sep+'terrain') 
    file=open(build_dir+dir_sep+'terrain'+dir_sep+file_name+'.ter','w')
    file.write('A\n800\nTERRAIN\n\n')
    [lat_med,lon_med]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
    half_meridian=pi*6378137
    texture_approx_size=int(2*half_meridian/2**(zoomlevel-4)*\
                        cos(lat_med*pi/180))
    file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 4096\n')
    file.write('BASE_TEX_NOWRAP ../textures/'+file_name+'.'+dds_or_png+'\n')
    if use_decal_on_terrain==True:
        file.write('DECAL_LIB lib/g10/decals/maquify_1_green_key.dcl\n')
    file.write('NO_SHADOW\n')
    file.close()
    return
##############################################################################

##############################################################################
# Les fichiers .ter de X-Plane (ici la version pour les lacs et rivières).
##############################################################################
def create_overlay_file(build_dir,file_name,til_x_left,til_y_top,zoomlevel,website):
    if not os.path.exists(build_dir+dir_sep+'terrain'):
        os.makedirs(build_dir+dir_sep+'terrain') 
    file=open(build_dir+dir_sep+'terrain'+dir_sep+file_name+\
            '_overlay.ter','w')
    file.write('A\n800\nTERRAIN\n\n')
    [lat_med,lon_med]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
    half_meridian=pi*6378137
    texture_approx_size=int(2*half_meridian/2**(zoomlevel-4)*\
                        cos(lat_med*pi/180))
    file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 4096\n')
    file.write('BASE_TEX_NOWRAP ../textures/'+file_name+'.'+dds_or_png+'\n')  
    file.write('WET\n')
    file.write('BORDER_TEX ../textures/water_transition.png\n')
    file.write('NO_SHADOW\n')
    file.close()
    return
##############################################################################

##############################################################################
# Les fichiers .ter de X-Plane (ici la version pour les mers et océans).
##############################################################################
def create_sea_overlay_file(build_dir,file_name,mask_name,til_x_left,til_y_top,\
        zoomlevel,website):
    if not os.path.exists(build_dir+dir_sep+'terrain'):
        os.makedirs(build_dir+dir_sep+'terrain') 
    file=open(build_dir+dir_sep+'terrain'+dir_sep+file_name+\
            '_sea_overlay.ter','w')
    file.write('A\n800\nTERRAIN\n\n')
    [lat_med,lon_med]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
    half_meridian=pi*6378137
    texture_approx_size=int(2*half_meridian/2**(zoomlevel-4)*\
                        cos(lat_med*pi/180))
    file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 4096\n')
    file.write('BASE_TEX_NOWRAP ../textures/'+file_name+'.'+dds_or_png+'\n')
    file.write('WET\n')
    file.write('BORDER_TEX ../textures/'+mask_name+'\n')
    file.write('NO_SHADOW\n')
    if use_additional_water_shader==True:
        file.write('TEXTURE_NORMAL 128 ../textures/water_normal_map.png\n')
        file.write('SPECULAR 0.2\n')
    file.close()
    return
##############################################################################

##############################################################################
#  Y a-t-il besoin de mettre un masque ?
##############################################################################
def which_mask(layer,strlat,strlon):
    tilx=layer[0]
    tily=layer[1]
    zoomlevel=layer[2]
    website=layer[3]
    factor=2**(zoomlevel-14)
    tilx14=(int(tilx/factor)//16)*16
    tily14=(int(tily/factor)//16)*16
    #rx=(tilx/factor)%16
    rx=int((tilx-factor*tilx14)/16)
    #ry=(tily/factor)%16
    ry=int((tily-factor*tily14)/16)
    mask_file_spec=Ortho4XP_dir+dir_sep+'Masks'+dir_sep+strlat+strlon+dir_sep+\
            str(int(tily14))+'_'+str(int(tilx14))+'_'+website+'.png'
    mask_file_gen=Ortho4XP_dir+dir_sep+'Masks'+dir_sep+strlat+strlon+dir_sep+\
            str(int(tily14))+'_'+str(int(tilx14))+'.png'
    if os.path.isfile(mask_file_spec):
        mask_file=mask_file_spec
    elif os.path.isfile(mask_file_gen):
        mask_file=mask_file_gen
    else:
        return 'None'
    big_img=Image.open(mask_file)
    x0=int(rx*4096/factor)
    y0=int(ry*4096/factor)
    small_img=big_img.crop((x0,y0,x0+4096//factor,y0+4096//factor))
    if not small_img.getbbox():
        return 'None'
    else:
        return [mask_file,factor,rx,ry]
##############################################################################
 
##############################################################################
#  La routine de conversion jpeg -> dds, avec éventuel calcul du masque alpha.
##############################################################################
def convert_texture(file_dir,file_name,website,build_dir):
    global busy_slots_conv
    busy_slots_conv+=1
    #print("Busy convert slots : "+str(busy_slots_conv))
    ctr_adj=0
    brt_adj=0
    sat_adj=0
    if website in contrast_adjust:
        ctr_adj=contrast_adjust[website]
    if website in brightness_adjust:
        brt_adj=brightness_adjust[website]
    if website in saturation_adjust:
        sat_adj=saturation_adjust[website]
    file_ext=".jpg"
    color_cmd=''
    if (website in full_color_correction) and  (full_color_correction[website]!=''):
        color_correction = full_color_correction[website]
        color_cmd = convert_cmd+' '+color_correction+' "'+\
                   file_dir+file_name+file_ext+'" "'+\
                   Ortho4XP_dir+dir_sep+'tmp'+dir_sep+file_name+'.png" '+devnull_rdir
    elif (ctr_adj!=0) or (brt_adj!=0) or (sat_adj!=0):
        color_cmd = convert_cmd+" -brightness-contrast "+\
                str(brt_adj)+"x"+str(ctr_adj)+\
                 " -modulate 100,"+str(100+sat_adj)+",100 "+\
                 '"'+file_dir+file_name+file_ext+'" "'+\
                 Ortho4XP_dir+dir_sep+'tmp'+dir_sep+file_name+'.png" '+devnull_rdir
    if color_cmd!='':
        os.system(color_cmd)
        conv_cmd=convert_cmd_bis +' "'+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+file_name+'.png" "'+\
                     build_dir+dir_sep+'textures'+dir_sep+file_name+'.'+dds_or_png+'" '+ devnull_rdir
        os.system(conv_cmd)
        try:
            os.remove(Ortho4XP_dir+dir_sep+'tmp'+dir_sep+file_name+'.png')
        except:
            pass  
    else:
        conv_cmd=convert_cmd_bis + ' "'+file_dir+file_name+file_ext+'" "'+build_dir+dir_sep+\
                   'textures'+dir_sep+file_name+'.'+dds_or_png+'" '+devnull_rdir
        os.system(conv_cmd)
    busy_slots_conv-=1
    return 
##############################################################################

##############################################################################
#  Le séquenceur de la phase de téléchargement des textures.
##############################################################################
def download_textures(strlat,strlon):
    global download_to_do_list,convert_to_do_list
    finished = False
    nbr_done=0
    nbr_done_or_in=0
    while finished != True:
        if download_to_do_list == []:
            time.sleep(0.1)
            try:
                if application.red_flag.get()==1:
                    print("Download process interrupted.")
                    return
            except:
                pass
        elif download_to_do_list[0] != 'finished':
            texture=download_to_do_list[0]
            [file_dir,file_name,file_ext]=filename_from_attributes(\
                               strlat,strlon,*texture)
            if os.path.isfile(file_dir+file_name+file_ext) != True:
                if verbose_output==True:
                    print("   Downloading missing orthophoto "+\
                      file_name+file_ext)
                build_jpeg_ortho(strlat,strlon,*texture)
                nbr_done+=1
                nbr_done_or_in+=1
                convert_to_do_list.append(texture)
            else:
                nbr_done_or_in+=1
                if verbose_output==True:
                    print("   The orthophoto "+file_name+file_ext+\
                                                    " is already present.")
                convert_to_do_list.append(texture)
            download_to_do_list.pop(0)
            try:
                application.progress_down.set(int(100*nbr_done_or_in/(nbr_done_or_in+len(download_to_do_list)))) 
                if application.red_flag.get()==1:
                    print("Download process interrupted.")
                    return
            except:
                pass
        else:
            finished=True
            try:
                application.progress_down.set(100) 
            except:
                pass
            if nbr_done >= 1:
                print("  Download of textures completed."+\
                      "                      ")
            convert_to_do_list.append('finished')
    return
##############################################################################


##############################################################################
#  Le séquenceur de la phase de conversion jpeg -> dds.
##############################################################################
def convert_textures(strlat,strlon,build_dir):
    global convert_to_do_list,busy_slots_conv
    busy_slots_conv=0
    nbr_done=0
    nbr_done_or_in=0
    if not os.path.exists(build_dir+dir_sep+'textures'):
            os.makedirs(build_dir+dir_sep+'textures')
    finished = False
    while finished != True:
        if convert_to_do_list == [] or busy_slots_conv >= max_convert_slots:
            time.sleep(0.1)
            try:
                if application.red_flag.get()==1:
                    print("Convert process interrupted.")
                    return
            except:
                pass
        elif convert_to_do_list[0] != 'finished':
            texture=convert_to_do_list.pop(0)
            [file_dir,file_name,file_ext]=filename_from_attributes(\
                                                    strlat,strlon,*texture)
            if (os.path.isfile(build_dir+dir_sep+'textures'+dir_sep+\
                 file_name+'.'+dds_or_png) != True ):
                if verbose_output==True:
                    print("   Converting orthophoto to build texture "
                      +file_name+'.'+dds_or_png+".")
                fargs_conv_text=[file_dir,file_name,texture[3],build_dir] 
                threading.Thread(target=convert_texture,args=fargs_conv_text).start()
                #convert_texture(file_dir,file_name,texture[3])
                #busy_slots_conv+=1
                #conv_text_thread.start()
                nbr_done+=1
                #print(" "+str(nbr_done)+" ")
                nbr_done_or_in+=1
                #sys.stdout.write("  Textures déjà converties : "\
                #        +str(nbr_done)+" (restent :"+\
                #        str(len(convert_to_do_list)-1)+")             \r") 
            else:
                nbr_done_or_in+=1
                if verbose_output==True:
                    print("   Texture file "+file_name+"."+dds_or_png+\
                      " already present.")

            try:
                application.progress_conv.set(int(100*nbr_done_or_in/(nbr_done_or_in+len(convert_to_do_list)))) 
                if application.red_flag.get()==1:
                    print("Conversion process interrupted.")
                    return
            except:
                pass
        else:
            finished=True
            if nbr_done >= 1:
                print("  Waiting for all convert threads to finish.")
                while busy_slots_conv > 0:
                    print("  ...")
                    time.sleep(3)
                application.progress_conv.set(100) 
                print("  Conversion of textures completed."+\
                      "                         ")
    return
##############################################################################


##############################################################################
#                                                                            #
#  VI: La méthode maître après le mailleur, elle attribue les textures et    #
#      crée au final le DSF.                                                 #
#                                                                            #
##############################################################################


##############################################################################
def build_dsf(lat0,lon0,ortho_list,water_overlay,\
        ratio_water,mesh_filename,build_dir):
    ####################################################################
    # The following is a simple web hit counter, it will count how much 
    # tiles are made by Ortho4XP. One aim is to get an idea of how much
    # we weight on OSM servers, the second is just curiosity.
    # Just comment the following lines if you do not wish your tiles
    # to be counted. 
    ####################################################################
    try:
        s=requests.Session()
        r=s.get("http://simplehitcounter.com/hit.php?uid=2163525&f=16777215&b=0",timeout=1)
        del(s)
        del(r)
    except:
        pass
    ######################################################

    global download_to_do_list,pools_max_points
    pool_cols           = 16
    pool_rows           = 16
    strlat='{:+.0f}'.format(lat0).zfill(3)
    strlon='{:+.0f}'.format(lon0).zfill(4)
    strlatround='{:+.0f}'.format(floor(lat0/10)*10).zfill(3)
    strlonround='{:+.0f}'.format(floor(lon0/10)*10).zfill(4)
    dest_dir=build_dir+dir_sep+'Earth nav data'+dir_sep+strlatround+\
            strlonround
    dsf_filename=dest_dir+dir_sep+strlat+strlon+'.dsf'
    
    print("-> Computing the required pool division") 
    f_mesh=open(mesh_filename,"r")
    for i in range(0,4):
        f_mesh.readline()
    pool_nbr=pool_rows*pool_cols
    pool_pt_count=numpy.zeros(pool_nbr,'uint32')
    nbr_pt_in=int(f_mesh.readline())
    for i in range(0,nbr_pt_in):
        tmplist=f_mesh.readline().split()
        lon=float(tmplist[0])
        lat=float(tmplist[1])
        pool_x=int((lon-lon0)*pool_cols)
        pool_y=int((lat-lat0)*pool_rows)
        if pool_x==pool_rows:
            pool_x-=1
        if pool_y==pool_cols:
            pool_y-=1
        pool_idx=(pool_y)*pool_cols+(pool_x)
        pool_pt_count[pool_idx]+=1
    maxptpool=numpy.max(pool_pt_count)
    #print(maxptpool)
    if maxptpool>=65355:
        pool_rows=pool_rows*2
        pool_cols=pool_cols*2
        print("   Pool division = 32")
    elif maxptpool<=16383:
        pool_rows=pool_rows//2
        pool_cols=pool_cols//2
        print("   Pool division = 8")
    else:
        print("   Pool division = 16")
    f_mesh.close()

    # test
    #pool_rows=16
    #pool_cols=16
    
    pool_nbr  = pool_rows*pool_cols
    pools_params=numpy.zeros((4*pool_nbr,18),'float32')
    pools_planes=numpy.zeros(4*pool_nbr,'uint32')
    pools_planes[0:pool_nbr]=7
    pools_planes[pool_nbr:2*pool_nbr]=5
    pools_planes[2*pool_nbr:4*pool_nbr]=9
    pools_lengths=numpy.zeros((4*pool_nbr),'uint32')
    try:
        pools=numpy.zeros((4*pool_nbr,9*pools_max_points),'uint16')
        pools_z_temp=numpy.zeros((4*pool_nbr,pools_max_points),'float32')
        pools_z_max=-9999*numpy.ones(4*pool_nbr,'float32')
        pools_z_min=9999*numpy.ones(4*pool_nbr,'float32')
    except:
        try:
            pools_max_points=pools_max_points//2
            pools=numpy.zeros((4*pool_nbr,9*pools_max_points),'uint16')
            pools_z_temp=numpy.zeros((4*pool_nbr,pools_max_points),'float32')
            pools_z_max=-9999*numpy.ones(4*pool_nbr,'float32')
            pools_z_min=9999*numpy.ones(4*pool_nbr,'float32')
            print("\nWARNING : Even though I won't use all of it, for speed purposes I must ")
            print("reserve an amount of RAM which you don't seem have available, I try")
            print("with half of it but it could be that the process has to stop.\n")
        except:
            try:
                pools_max_points=pools_max_points//2
                pools=numpy.zeros((4*pool_nbr,9*pools_max_points),'uint16')
                pools_z_temp=numpy.zeros((4*pool_nbr,pools_max_points),'float32')
                pools_z_max=-9999*numpy.ones(4*pool_nbr,'float32')
                pools_z_min=9999*numpy.ones(4*pool_nbr,'float32')
                print("\nWARNING : Even though I won't use all of it, for speed purposes I must ")
                print("reserve an amount of RAM which you don't seem have available, I try")
                print("with one fourth of it but it could be that the process has to stop.\n")
            except:
                return
    dico_new_pt={}
    dico_textures={'terrain_Water':0,'None':1}
    terrain_def="terrain_Water\0lib/g10/terrain10/fruit_tmp_wet_hill.ter\0"
    textures={}
    textures[0]=collections.defaultdict(list)
    textures[1]=collections.defaultdict(list)
    skipped_sea_textures=[]
    dico_mask={}

    # initialization of the pools parameters
    
    for pool_y in range(0,pool_rows):       
        for pool_x in range(0,pool_cols):  
            pool_idx=(pool_y)*pool_cols+(pool_x)
            pools_params[pool_idx,0]=1/pool_cols
            pools_params[pool_idx,1]=lon0+pool_x/pool_cols # lon
            pools_params[pool_idx,2]=1/pool_rows
            pools_params[pool_idx,3]=lat0+pool_y/pool_rows # lat 
            pools_params[pool_idx,4]=0
            pools_params[pool_idx,5]=0             # z (temp)
            pools_params[pool_idx,6]=2     
            pools_params[pool_idx,7]=-1            # u 
            pools_params[pool_idx,8]=2     
            pools_params[pool_idx,9]=-1            # v
            pools_params[pool_idx,10]=1    
            pools_params[pool_idx,11]=0            # s
            pools_params[pool_idx,12]=1    
            pools_params[pool_idx,13]=0            # t
            pools_params[pool_idx,14]=1    
            pools_params[pool_idx,15]=0            # bs
            pools_params[pool_idx,16]=1    
            pools_params[pool_idx,17]=0            # bt
    pools_params[pool_nbr:2*pool_nbr]=pools_params[0:pool_nbr]
    pools_params[2*pool_nbr:3*pool_nbr]=pools_params[0:pool_nbr]
    pools_params[3*pool_nbr:4*pool_nbr]=pools_params[0:pool_nbr]
    
    # We start by encoding the 5 coordinates (x,y,z,u,v) of the physical points of
    # the mesh into the array pt_in
    
    f_mesh=open(mesh_filename,"r")
    for i in range(0,4):
        f_mesh.readline()
    nbr_pt_in=int(f_mesh.readline())
    pt_in=numpy.zeros(5*nbr_pt_in,'float')
    for i in range(0,nbr_pt_in):
        tmplist=f_mesh.readline().split()
        pt_in[5*i]=float(tmplist[0])
        pt_in[5*i+1]=float(tmplist[1])
        pt_in[5*i+2]=float(tmplist[2])
    for i in range(0,3):
        f_mesh.readline()
    for i in range(0,nbr_pt_in):
        tmplist=f_mesh.readline().split()
        pt_in[5*i+3]=float(tmplist[0])
        pt_in[5*i+4]=float(tmplist[1])
   
    # Next, we go through the Triangle section of the mesh file and build DSF 
    # mesh points (these take into accound texture as well), point pools, etc. 
    
    for i in range(0,2): # skip 2 lines
        f_mesh.readline()
    nbr_tri_in=int(f_mesh.readline()) # read nbr of tris
    len_dico_new_pt=0
    total_cross_pool=0
    step_stones=nbr_tri_in//100
    percent=-1
    for i in range(0,nbr_tri_in):
        if i%step_stones==0:
            percent+=1
            try:
                application.progress_attr.set(int(percent*9/10))
                if application.red_flag.get()==1:
                    print("Attribution process interrupted.")
                    return
            except:
                pass
        tmplist=f_mesh.readline().split()
        # look for the texture that will possibly cover the tri
        n1=int(tmplist[0])-1
        n2=int(tmplist[1])-1
        n3=int(tmplist[2])-1
        tri_type=tmplist[3] 
        if int(tri_type)>=4:
            tri_type='0'
        [lon1,lat1,z1,u1,v1]=pt_in[5*n1:5*n1+5]
        [lon2,lat2,z2,u2,v2]=pt_in[5*n2:5*n2+5]
        [lon3,lat3,z3,u3,v3]=pt_in[5*n3:5*n3+5]
        texture=attribute_texture(lat1,lon1,lat2,lon2,lat3,lon3,ortho_list,tri_type)
        
        # do we need to download a texture and/or to create a ter file ?       
        if (tri_type=='0'):
            if str(texture) in dico_textures: # 'None' is in dico_textures by definition
                texture_idx=dico_textures[str(texture)]
            else:
                texture_idx=len(dico_textures)
                dico_textures[str(texture)]=texture_idx
                textures[texture_idx]=collections.defaultdict(list)
                [file_dir,file_name,file_ext]=\
                        filename_from_attributes(strlat,strlon,*texture)
                if ((str(texture)+'_overlay') not in dico_textures) and \
                           ((str(texture)+'_sea_overlay') not in dico_textures):
                    if (os.path.isfile(build_dir+dir_sep+'textures'+dir_sep+\
                            file_name+'.'+dds_or_png) != True ):
                        download_to_do_list.append(texture)
                    else:
                        if verbose_output==True:
                            print("   Texture file "+file_name+"."+dds_or_png+\
                            " already present.")
                create_terrain_file(build_dir,file_name,*texture)
                terrain_def+='terrain/'+file_name+'.ter\0' 
            texture_overlay_idx=-1
        elif water_option in [2,3]:
            texture_idx=0
            #if (tri_type=='1' and use_masks_for_inland==False) and (texture != 'None'):
            if (texture != 'None') and ((tri_type=='1' and use_masks_for_inland==False) or int(texture[2])<14):
                if str(texture)+'_overlay' in dico_textures:
                    texture_overlay_idx=dico_textures[str(texture)+'_overlay']
                else:
                    texture_overlay_idx=len(dico_textures)
                    dico_textures[str(texture)+'_overlay']=texture_overlay_idx
                    textures[texture_overlay_idx]=collections.defaultdict(list)
                    [file_dir,file_name,file_ext]=\
                            filename_from_attributes(strlat,strlon,*texture)
                    if (str(texture) not in dico_textures) and \
                            ((str(texture)+'_sea_overlay') not in dico_textures):
                        if (os.path.isfile(build_dir+dir_sep+'textures'+dir_sep+\
                            file_name+'.'+dds_or_png) != True ):
                            download_to_do_list.append(texture)
                        else:
                            if verbose_output==True:
                                print("   Texture file "+file_name+"."+dds_or_png+\
                                " already present.")
                    create_overlay_file(build_dir,file_name,*texture)
                    terrain_def+='terrain/'+file_name+'_overlay.ter\0' 
            elif (texture != 'None') and (tri_type in ['2','3'] or use_masks_for_inland==True) :
                if str(texture)+'_sea_overlay' in dico_textures:
                    texture_overlay_idx=dico_textures[str(texture)+'_sea_overlay']
                elif str(texture) not in skipped_sea_textures:
                    mask_data = which_mask(texture,strlat,strlon)
                    dico_mask[str(texture)]=mask_data
                    if mask_data != 'None':
                        if verbose_output==True:
                            print("      Use of an alpha mask.")
                        mask_name=mask_data[0].split(dir_sep)[-1]
                        if os.path.isfile(build_dir+dir_sep+'textures'+dir_sep+\
                             mask_name) != True:
                            os.system(copy_cmd+' "'+mask_data[0]+'" "'+build_dir+\
                             dir_sep+'textures'+dir_sep+mask_name+'" '+devnull_rdir)
                        texture_overlay_idx=len(dico_textures)
                        dico_textures[str(texture)+'_sea_overlay']=texture_overlay_idx
                        textures[texture_overlay_idx]=collections.defaultdict(list)
                        [file_dir,file_name,file_ext]=\
                                filename_from_attributes(strlat,strlon,*texture)
                        if (str(texture) not in dico_textures) and \
                            ((str(texture)+'_overlay') not in dico_textures):
                            if (os.path.isfile(build_dir+dir_sep+'textures'+dir_sep+\
                                file_name+'.'+dds_or_png) != True ):
                                download_to_do_list.append(texture)
                            else:
                                if verbose_output==True:
                                    print("   Texture file "+file_name+"."+dds_or_png+\
                                    " already present.")
                        create_sea_overlay_file(build_dir,file_name,mask_name,*texture)
                        terrain_def+='terrain/'+file_name+'_sea_overlay.ter\0' 
                    else:    
                        skipped_sea_textures.append(str(texture))
                        texture_overlay_idx=-1
                else:
                    texture_overlay_idx=-1
            else: # texture = 'None'
                texture_overlay_idx=-1
        else:  # water_overlay = False
            texture_idx=0
            texture_overlay_idx=-1
        
        # now we put the tri in the right texture(s)   
        tri_p=[]
        if tri_type == '0':
            for n in [n1,n3,n2]:     # beware of ordering for orientation ! 
                if str(n)+'_'+str(texture_idx) in dico_new_pt:
                    [pool_idx,pos_in_pool]=dico_new_pt[str(n)+'_'+str(texture_idx)]
                else:
                    [lon,lat,z,u,v]=pt_in[5*n:5*n+5]
                    if texture!='None':
                        [s,t]=st_coord(lat,lon,*texture)
                    else:
                        [s,t]=[0,0]
                    len_dico_new_pt+=1
                    [pool_idx,pool_nx,pool_ny]=point_params(lat,lon,lat0,lon0,\
                            pools_params,pool_cols,pool_rows)
                    pos_in_pool=pools_lengths[pool_idx]
                    dico_new_pt[str(n)+'_'+str(texture_idx)]=[pool_idx,pos_in_pool]
                    pools[pool_idx,7*pos_in_pool:7*pos_in_pool+7]=[pool_nx,\
                            pool_ny,0,round((1+normal_map_strength*u)/2*65535),round((1+normal_map_strength*v)/2*65535),\
                            round(s*65535),round(t*65535)]
                    pools_z_temp[pool_idx,pos_in_pool]=z
                    pools_z_max[pool_idx] = pools_z_max[pool_idx] if pools_z_max[pool_idx] >= z else z
                    pools_z_min[pool_idx] = pools_z_min[pool_idx] if pools_z_min[pool_idx] <= z else z
                    pools_lengths[pool_idx]+=1
                    if pools_lengths[pool_idx]==pools_max_points:
                        print("We have reached the maximum allowed number of points in the pool\n",
                              "centered at lat=", pools_params[pool_idx,3]+\
                              0.5*pools_params[pool_idx,2]," lon=",pools_params[pool_idx,1]+\
                              0.5*pools_params[pool_idx,0])
                        print("You should try the following : 1) test with a higher value of curv_tol (say 3 and \n"+\
                              "then lower untill before it breaks) 2) if it still doesn't work, look for an error on \n"+\
                              "OpenStreetMap (presumably encroached water segments or two nodes that should be one) in \n"+\
                              "a 1 mile radius of the indicated point.")
                        print("")
                        print("Failure.")
                        print('_____________________________________________________________'+\
                              '____________________________________')
                        return
                tri_p+=[pool_idx,pos_in_pool]
            if tri_p[0]==tri_p[2] and tri_p[2]==tri_p[4]:
                pool_idx=tri_p[0]
                textures[texture_idx][pool_idx]+=[tri_p[1],tri_p[3],tri_p[5]]    
            else:
                total_cross_pool+=1
                pool_idx='cross-pool'
                textures[texture_idx][pool_idx]+=tri_p
        else: # water 
            # first x-plane water
            for n in [n1,n3,n2]:     # beware of ordering for orientation ! 
                if str(n)+'_0' in dico_new_pt:
                    [pool_idx,pos_in_pool]=dico_new_pt[str(n)+'_0']
                else:
                    [lon,lat,z,u,v]=pt_in[5*n:5*n+5]
                    len_dico_new_pt+=1
                    [pool_idx,pool_nx,pool_ny]=point_params(lat,lon,lat0,lon0,\
                            pools_params,pool_cols,pool_rows)
                    pool_idx+=pool_nbr # --> we start x-plane water pools at pool_nbr idx
                    pos_in_pool=pools_lengths[pool_idx]
                    dico_new_pt[str(n)+'_0']=[pool_idx,pos_in_pool]
                    pools[pool_idx,5*pos_in_pool:5*pos_in_pool+5]=[pool_nx,\
                            pool_ny,0,32768,32768]
                    pools_z_temp[pool_idx,pos_in_pool]=z
                    pools_z_max[pool_idx] = pools_z_max[pool_idx] if pools_z_max[pool_idx] >= z else z
                    pools_z_min[pool_idx] = pools_z_min[pool_idx] if pools_z_min[pool_idx] <= z else z
                    pools_lengths[pool_idx]+=1
                    if pools_lengths[pool_idx]==pools_max_points:
                        print("We have reached the maximum allowed number of points in the pool\n",
                              "centered at lat=", pools_params[pool_idx,3]+\
                              0.5*pools_params[pool_idx,2]," lon=",pools_params[pool_idx,1]+\
                              0.5*pools_params[pool_idx,0])
                        print("You should try the following : 1) test with a higher value of curv_tol (say 3 and \n"+\
                              "then lower untill before it breaks) 2) if it still doesn't work, look for an error on \n"+\
                              "OpenStreetMap (presumably encroached water segments or two nodes that should be one) in \n"+\
                              "a 1 mile radius of the indicated point.")
                        print("")
                        print("Failure.")
                        print('_____________________________________________________________'+\
                              '____________________________________')
                        return
                tri_p+=[pool_idx,pos_in_pool]
            if tri_p[0]==tri_p[2] and tri_p[2]==tri_p[4]:
                pool_idx=tri_p[0]
                textures[0][pool_idx]+=[tri_p[1],tri_p[3],tri_p[5]]    
            else:
                total_cross_pool+=1
                pool_idx='cross-pool'
                textures[0][pool_idx]+=tri_p
            # next possibly overlays
            if water_overlay==False:
                continue
            if texture_overlay_idx!=-1 and ((tri_type=='1'and use_masks_for_inland==False) or int(texture[2])<14):
                tri_p=[]
                for n in [n1,n3,n2]:     # beware of ordering for orientation ! 
                    if str(n)+'_'+str(texture_overlay_idx) in dico_new_pt:
                        [pool_idx,pos_in_pool]=dico_new_pt[str(n)+'_'+str(texture_overlay_idx)]
                    else:
                        [lon,lat,z,u,v]=pt_in[5*n:5*n+5]
                        [s,t]=st_coord(lat,lon,*texture)
                        len_dico_new_pt+=1
                        [pool_idx,pool_nx,pool_ny]=point_params(lat,lon,lat0,lon0,\
                                pools_params,pool_cols,pool_rows)
                        pool_idx+=2*pool_nbr  # we start textured water pools after x-plane water pools
                        pos_in_pool=pools_lengths[pool_idx]
                        dico_new_pt[str(n)+'_'+str(texture_overlay_idx)]=[pool_idx,pos_in_pool]
                        pools[pool_idx,9*pos_in_pool:9*pos_in_pool+9]=\
                                [pool_nx,pool_ny,0,32768,32768,round(s*65535),\
                                 round(t*65535),0,round(ratio_water*65535)]
                        pools_z_temp[pool_idx,pos_in_pool]=z
                        pools_z_max[pool_idx] = pools_z_max[pool_idx] \
                                      if pools_z_max[pool_idx] >= z else z
                        pools_z_min[pool_idx] = pools_z_min[pool_idx] \
                                      if pools_z_min[pool_idx] <= z else z
                        pools_lengths[pool_idx]+=1
                        if pools_lengths[pool_idx]==pools_max_points:
                            print("We have reached the maximum allowed number of points in the pool\n",
                                  "centered at lat=", pools_params[pool_idx,3]+\
                                0.5*pools_params[pool_idx,2]," lon=",pools_params[pool_idx,1]+\
                                0.5*pools_params[pool_idx,0])
                            print("You should try the following : 1) test with a higher value of curv_tol (say 3 and \n"+\
                                  "then lower untill before it breaks) 2) if it still doesn't work, look for an error on \n"+\
                                  "OpenStreetMap (presumably encroached water segments or two nodes that should be one) in \n"+\
                                  "a 1 mile radius of the indicated point.")
                            print("")
                            print("Failure.")
                            print('_____________________________________________________________'+\
                              '____________________________________')
                            return
                    tri_p+=[pool_idx,pos_in_pool]
                if tri_p[0]==tri_p[2] and tri_p[2]==tri_p[4]:
                    pool_idx=tri_p[0]
                    textures[texture_overlay_idx][pool_idx]+=[tri_p[1],tri_p[3],tri_p[5]]
                    #textures[0][pool_idx]+=[tri_p[1],tri_p[3],tri_p[5]]
                else:
                    total_cross_pool+=1
                    pool_idx='cross-pool'
                    textures[texture_overlay_idx][pool_idx]+=tri_p
                    #textures[0][pool_idx]+=tri_p
            elif texture_overlay_idx!=-1 and (tri_type in ['2','3'] or use_masks_for_inland==True):
                tri_p=[]
                for n in [n1,n3,n2]:     # beware of ordering for orientation ! 
                    if str(n)+'_'+str(texture_overlay_idx) in dico_new_pt:
                        [pool_idx,pos_in_pool]=dico_new_pt[str(n)+'_'+str(texture_overlay_idx)]
                    else:
                        [lon,lat,z,u,v]=pt_in[5*n:5*n+5]
                        [s,t]=st_coord(lat,lon,*texture)
                        len_dico_new_pt+=1
                        [pool_idx,pool_nx,pool_ny]=point_params(lat,lon,lat0,lon0,\
                                pools_params,pool_cols,pool_rows)
                        pool_idx+=3*pool_nbr  # we end with textured sea water pools
                        pos_in_pool=pools_lengths[pool_idx]
                        dico_new_pt[str(n)+'_'+str(texture_overlay_idx)]=[pool_idx,pos_in_pool]
                        [ms,mt]=st_coord(lat,lon,texture[0],texture[1],texture[2],'BI') # Masks are always in epsg:4326!
                        mask_data=dico_mask[str(texture)]
                        rx=float(mask_data[2])
                        ry=float(mask_data[3])
                        factor=float(mask_data[1])
                        bs=rx/factor+ms/factor
                        bt=1-ry/factor+(mt-1)/factor
                        pools[pool_idx,9*pos_in_pool:9*pos_in_pool+9]=[pool_nx,\
                                  pool_ny,0,32768,32768,round(s*65535),round(t*65535),\
                                  round(bs*65535),round(bt*65535)]
                        pools_z_temp[pool_idx,pos_in_pool]=z
                        pools_z_max[pool_idx] = pools_z_max[pool_idx]\
                                        if pools_z_max[pool_idx] >= z else z
                        pools_z_min[pool_idx] = pools_z_min[pool_idx] \
                                        if pools_z_min[pool_idx] <= z else z
                        pools_lengths[pool_idx]+=1
                        if pools_lengths[pool_idx]==pools_max_points:
                            print("We have reached the maximum allowed number of points in the pool\n",
                                  "centered at lat=", pools_params[pool_idx,3]+\
                                0.5*pools_params[pool_idx,2]," lon=",pools_params[pool_idx,1]+\
                                0.5*pools_params[pool_idx,0])
                            print("You should try the following : 1) test with a higher value of curv_tol (say 3 and \n"+\
                                  "then lower untill before it breaks) 2) if it still doesn't work, look for an error on \n"+\
                                  "OpenStreetMap (presumably encroached water segments or two nodes that should be one) in \n"+\
                                  "a 1 mile radius of the indicated point.")
                            print("")
                            print("Failure.")
                            print('_____________________________________________________________'+\
                              '____________________________________')
                            return
                    tri_p+=[pool_idx,pos_in_pool]
                if tri_p[0]==tri_p[2] and tri_p[2]==tri_p[4]:
                    pool_idx=tri_p[0]
                    textures[texture_overlay_idx][pool_idx]+=\
                            [tri_p[1],tri_p[3],tri_p[5]]
                    #textures[0][pool_idx]+=[tri_p[1],tri_p[3],tri_p[5]]
                else:
                    total_cross_pool+=1
                    pool_idx='cross-pool'
                    textures[texture_overlay_idx][pool_idx]+=tri_p
                    #textures[0][pool_idx]+=tri_p
    f_mesh.close()
    download_to_do_list.append('finished')
    os.system(copy_cmd+' "'+Ortho4XP_dir+dir_sep+'Utils'+dir_sep+\
             'water_transition.png'+'" "'+build_dir+dir_sep+'textures'+\
              dir_sep+'" '+devnull_rdir) 
    print("  Encoding of the DSF file...")  
    if verbose_output==True:
        print("   Final nbr of points : "+str(len_dico_new_pt))
        print("   Final nbr of cross pool tris: "+str(total_cross_pool))
    for i in range(0,pool_nbr):
        #print(pools_lengths[i])
        if pools_lengths[i]>=35000 and pool_cols==32:
            print("A suspicious number (although non blocking) nbr of points was found\n"+\
                  "in the zone centered in lat=",pools_params[i,3]+0.5*pools_params[i,2],\
                  " lon=",pools_params[i,1]+0.5*pools_params[i,0]," : ",pools_lengths[i],".")
            print("That could be related to an OSM error, but also to a too large number of")
            print("triangles due to a too low value of the parameter curv_tol (cfr log in Step 2).")
    for pool_idx in range(0,4*pool_nbr):
        pools_params[pool_idx,5]=pools_z_min[pool_idx]*100000
        pools_params[pool_idx,4]=(pools_z_max[pool_idx]-pools_z_min[pool_idx])*100000 +100
        for pos_in_pool in range(0,pools_lengths[pool_idx]):
            pools[pool_idx,pools_planes[pool_idx]*pos_in_pool+2]=int(round((pools_z_temp[pool_idx,\
                    pos_in_pool]*100000-pools_params[pool_idx,5])/pools_params[pool_idx,4]*65535))

    # Now is time to write our DSF to disk, the exact binary format is described on the wiki
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    if os.path.exists(dest_dir+dir_sep+dsf_filename+'.dsf'):
        os.system(copy_cmd+' "'+dest_dir+dir_sep+dsf_file+'.dsf'+'" "'+\
         dest_dir+dir_sep+dsf_file+'.dsf.bak" '+devnull_rdir)
    
    properties="sim/west\0"+str(lon0)+"\0"+"sim/east\0"+str(lon0+1)+"\0"+\
               "sim/south\0"+str(lat0)+"\0"+"sim/north\0"+str(lat0+1)+"\0"+\
               "sim/creation_agent\0"+"Ortho4XP\0"

    # Computation of intermediate and of total length 
    size_of_prop_string=len(properties)
    size_of_terrain_string=len(terrain_def)
    size_of_head_atom=16+size_of_prop_string
    size_of_prop_atom=8+size_of_prop_string
    size_of_defn_atom=48+size_of_terrain_string
    size_of_tert_atom=8+size_of_terrain_string
    size_of_geod_atom=8
    for k in range(0,4*pool_nbr):
        if pools_lengths[k]>0:
            size_of_geod_atom+=21+pools_planes[k]*(9+2*pools_lengths[k])
    if verbose_output==True:
        print("   Size of DEFN atom : "+str(size_of_defn_atom)+" bytes.")    
        print("   Size of GEOD atom : "+str(size_of_geod_atom)+" bytes.")    
    f=open(dsf_filename,'wb')
    f.write(b'XPLNEDSF')
    f.write(struct.pack('<I',1))
    
    # Head super-atom
    f.write(b"DAEH")
    f.write(struct.pack('<I',size_of_head_atom))
    f.write(b"PORP")
    f.write(struct.pack('<I',size_of_prop_atom))
    f.write(bytes(properties,'ascii'))
    
    # Definitions super-atom
    f.write(b"NFED")
    f.write(struct.pack('<I',size_of_defn_atom))
    f.write(b"TRET")
    f.write(struct.pack('<I',size_of_tert_atom))
    f.write(bytes(terrain_def,'ascii'))
    f.write(b"TJBO")
    f.write(struct.pack('<I',8))
    f.write(b"YLOP")
    f.write(struct.pack('<I',8))
    f.write(b"WTEN")
    f.write(struct.pack('<I',8))
    f.write(b"NMED")
    f.write(struct.pack('<I',8))
    
    # Geodata super-atom
    f.write(b"DOEG")
    f.write(struct.pack('<I',size_of_geod_atom))
    for k in range(0,4*pool_nbr):
        if pools_lengths[k]==0:
            continue
        f.write(b'LOOP')
        f.write(struct.pack('<I',13+pools_planes[k]+2*pools_planes[k]*pools_lengths[k]))
        f.write(struct.pack('<I',pools_lengths[k]))
        f.write(struct.pack('<B',pools_planes[k]))
        for l in range(0,pools_planes[k]):
            f.write(struct.pack('<B',0))
            for m in range(0,pools_lengths[k]):
                f.write(struct.pack('<H',pools[k,pools_planes[k]*m+l]))
    for k in range(0,4*pool_nbr):
        if pools_lengths[k]==0:
            continue
        f.write(b'LACS')
        f.write(struct.pack('<I',8+8*pools_planes[k]))
        for l in range(0,2*pools_planes[k]):
            f.write(struct.pack('<f',pools_params[k,l]))
   
    try:
        application.progress_attr.set(95)
        if application.red_flag.get()==1:
            print("Attribution process interrupted.")
            return
    except:
        pass
    # Since we possibly skipped some pools, we rebuild a dico
    # which tells the pool position in the dsf of a pool prior
    # to the stripping :

    dico_new_pool={}
    new_pool_idx=0
    for k in range(0,4*pool_nbr):
        if pools_lengths[k] != 0:
            dico_new_pool[k]=new_pool_idx
            new_pool_idx+=1

    # Commands atom
    
    # we first compute its size :
    size_of_cmds_atom=8
    for texture_idx in textures:
        if len(textures[texture_idx])==0:
            continue
        size_of_cmds_atom+=3
        for pool_idx in textures[texture_idx]:
            if pool_idx != 'cross-pool':
                size_of_cmds_atom+= 13+2*(len(textures[texture_idx][pool_idx])+\
                        ceil(len(textures[texture_idx][pool_idx])/255))
            else:
                size_of_cmds_atom+= 13+2*(len(textures[texture_idx][pool_idx])+\
                        ceil(len(textures[texture_idx][pool_idx])/510))
    if verbose_output==True:
        print("   Size of CMDS atom : "+str(size_of_cmds_atom)+" bytes.")
    f.write(b'SDMC')                               # CMDS header 
    f.write(struct.pack('<I',size_of_cmds_atom))   # CMDS length
    
    for texture_idx in textures:
        if len(textures[texture_idx])==0:
            continue
        #print("texture_idx = "+str(texture_idx))
        f.write(struct.pack('<B',4))           # SET DEFINITION 16
        f.write(struct.pack('<H',texture_idx)) # TERRAIN INDEX
        flag=1   # physical
        for pool_idx in textures[texture_idx]:
            if pool_idx!='cross-pool':
                if pools_planes[pool_idx]==9:
                    #print("overlay flag set !")
                    flag=2 #overlay
            else:
                if pools_planes[textures[texture_idx]['cross-pool'][0]]==9:
                    flag=2
        for pool_idx in textures[texture_idx]:
            #print("  pool_idx = "+str(pool_idx))
            if pool_idx != 'cross-pool':
                f.write(struct.pack('<B',1))                          # POOL SELECT
                f.write(struct.pack('<H',dico_new_pool[pool_idx]))    # POOL INDEX
    
                f.write(struct.pack('<B',18))    # TERRAIN PATCH FLAGS AND LOD
                f.write(struct.pack('<B',flag))  # FLAG
                f.write(struct.pack('<f',0))     # NEAR LOD
                f.write(struct.pack('<f',-1))    # FAR LOD
                
                blocks=floor(len(textures[texture_idx][pool_idx])/255)
                #print("     "+str(blocks)+" blocks")    
                for j in range(0,blocks):
                    f.write(struct.pack('<B',23))   # PATCH TRIANGLE
                    f.write(struct.pack('<B',255))  # COORDINATE COUNT

                    for k in range(0,255):
                        f.write(struct.pack('<H',textures[texture_idx][pool_idx][255*j+k]))  # COORDINATE IDX
                remaining_tri_p=len(textures[texture_idx][pool_idx])%255
                if remaining_tri_p != 0:
                    f.write(struct.pack('<B',23))               # PATCH TRIANGLE
                    f.write(struct.pack('<B',remaining_tri_p))  # COORDINATE COUNT
                    for k in range(0,remaining_tri_p):
                        f.write(struct.pack('<H',textures[texture_idx][pool_idx][255*blocks+k]))  # COORDINATE IDX
            elif pool_idx == 'cross-pool':
                pool_idx_init=textures[texture_idx][pool_idx][0]
                f.write(struct.pack('<B',1))                               # POOL SELECT
                f.write(struct.pack('<H',dico_new_pool[pool_idx_init]))    # POOL INDEX
                f.write(struct.pack('<B',18))    # TERRAIN PATCH FLAGS AND LOD
                f.write(struct.pack('<B',flag))  # FLAG
                f.write(struct.pack('<f',0))     # NEAR LOD
                f.write(struct.pack('<f',-1))  # FAR LOD
                
                blocks=floor(len(textures[texture_idx][pool_idx])/510)
                for j in range(0,blocks):
                    f.write(struct.pack('<B',24))   # PATCH TRIANGLE CROSS-POOL
                    f.write(struct.pack('<B',255))  # COORDINATE COUNT
                    for k in range(0,255):
                        f.write(struct.pack('<H',dico_new_pool[textures[texture_idx][pool_idx][510*j+2*k]]))    # POOL IDX
                        f.write(struct.pack('<H',textures[texture_idx][pool_idx][510*j+2*k+1]))                 # POS_IN_POOL IDX
                remaining_tri_p=int((len(textures[texture_idx][pool_idx])%510)/2)
                if remaining_tri_p != 0:
                    f.write(struct.pack('<B',24))               # PATCH TRIANGLE CROSS-POOL
                    f.write(struct.pack('<B',remaining_tri_p))  # COORDINATE COUNT
                    for k in range(0,remaining_tri_p):
                        f.write(struct.pack('<H',dico_new_pool[textures[texture_idx][pool_idx][510*blocks+2*k]]))   # POOL IDX
                        f.write(struct.pack('<H',textures[texture_idx][pool_idx][510*blocks+2*k+1]))                # POS_IN_PO0L IDX
    try:
        application.progress_attr.set(98)
        if application.red_flag.get()==1:
            print("Attribution process interrupted.")
            return
    except:
        pass
    f.close()
    f=open(dsf_filename,'rb')
    data=f.read()
    m=hashlib.md5()
    m.update(data)
    #print(str(m.digest_size))
    md5sum=m.digest()
    #print(str(md5sum))
    f.close()
    f=open(dsf_filename,'ab')
    f.write(md5sum)
    f.close()
    try:
        application.progress_attr.set(100)
    except:
        pass
    print("  DSF file encoded, total size is  : "+str(28+size_of_head_atom+\
            size_of_defn_atom+size_of_geod_atom+size_of_cmds_atom)+" bytes.")
    return
##############################################################################


##############################################################################
def point_params(lat,lon,lat0,lon0,pools_params,pool_cols,pool_rows):
    pool_x=int((lon-lon0)*pool_cols)
    pool_y=int((lat-lat0)*pool_rows)
    if pool_x==pool_rows:
        pool_x-=1
    if pool_y==pool_cols:
        pool_y-=1
    pool_idx=(pool_y)*(pool_cols)+(pool_x)
    pool_nx=int(round((lon-pools_params[pool_idx][1])/\
            pools_params[pool_idx][0]*65535))
    pool_ny=int(round((lat-pools_params[pool_idx][3])/\
            pools_params[pool_idx][2]*65535))
    return [pool_idx,pool_nx,pool_ny]
##############################################################################

####
#Test
####
def build_pools_params(lat0,lon0,pool_cols,pool_rows):
    pool_nbr=pool_rows*pool_cols
    pools_params=numpy.zeros((4*pool_nbr,18),'float32')
    for pool_y in range(0,pool_rows):       
        for pool_x in range(0,pool_cols):  
            pool_idx=(pool_y)*pool_cols+(pool_x)
            pools_params[pool_idx,0]=1/pool_cols*(65536/65535)
            pools_params[pool_idx,1]=lon0+pool_x/pool_cols # lon
            pools_params[pool_idx,2]=1/pool_rows
            pools_params[pool_idx,3]=lat0+pool_y/pool_rows # lat 
            pools_params[pool_idx,4]=0
            pools_params[pool_idx,5]=0             # z (temp)
            pools_params[pool_idx,6]=2     
            pools_params[pool_idx,7]=-1            # u 
            pools_params[pool_idx,8]=2     
            pools_params[pool_idx,9]=-1            # v
            pools_params[pool_idx,10]=1    
            pools_params[pool_idx,11]=0            # s
            pools_params[pool_idx,12]=1    
            pools_params[pool_idx,13]=0            # t
            pools_params[pool_idx,14]=1    
            pools_params[pool_idx,15]=0            # bs
            pools_params[pool_idx,16]=1    
            pools_params[pool_idx,17]=0            # bt
    pools_params[pool_nbr:2*pool_nbr]=pools_params[0:pool_nbr]
    pools_params[2*pool_nbr:3*pool_nbr]=pools_params[0:pool_nbr]
    pools_params[3*pool_nbr:4*pool_nbr]=pools_params[0:pool_nbr]
    return pools_params


def build_tile(lat,lon,build_dir,mesh_filename,clean_tmp_files):
    global download_to_do_list,convert_to_do_list
    download_to_do_list=[]
    convert_to_do_list=[]
    t3=time.time()
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    fargs_dsf=[lat,lon,ortho_list,\
            water_overlay,ratio_water,mesh_filename,build_dir] 
    if clean_unused_dds_and_ter_files==True:
        print("Purging old .ter files")
        if os.path.exists(build_dir+dir_sep+'terrain'):
            for oldterfile in os.listdir(build_dir+dir_sep+'terrain'):
                os.remove(build_dir+dir_sep+'terrain'+dir_sep+oldterfile)
    build_dsf_thread=threading.Thread(target=build_dsf,args=fargs_dsf)
    fargs_down=[strlat,strlon]
    download_thread=threading.Thread(target=download_textures,args=fargs_down)
    fargs_conv=[strlat,strlon,build_dir]
    convert_thread=threading.Thread(target=convert_textures,args=fargs_conv)
    try:
        application.red_flag.set(0)
        application.progress_attr.set(0) 
        application.progress_down.set(0) 
        application.progress_conv.set(0) 
    except:
        pass
    print("Start of the texture attribution process...")
    build_dsf_thread.start()
    #build_dsf_thread.join()
    if skip_downloads != True:
        download_thread.start()
        if skip_converts != True:
            convert_thread.start()
    build_dsf_thread.join()
    if skip_downloads != True:
        download_thread.join()
        if skip_converts != True:
            convert_thread.join()
    if clean_unused_dds_and_ter_files==True:
        print("Purging non necessary .dds files")
        for oldfilename in os.listdir(build_dir+dir_sep+'textures'):
            try:
                [oldfilenamebase,oldfilenameext]=oldfilename.split('.')
            except:
                continue
            if oldfilenameext!='dds':
                    continue
            if os.path.isfile(build_dir+dir_sep+'terrain'+dir_sep+oldfilenamebase+'.ter'):
                continue
            if os.path.isfile(build_dir+dir_sep+'terrain'+dir_sep+oldfilenamebase+'_overlay.ter'):
                continue
            if os.path.isfile(build_dir+dir_sep+'terrain'+dir_sep+oldfilenamebase+'_sea_overlay.ter'):
                continue
            # if we have reached here we are facing a dds which is no longer need and therefore we delete it
            print("  -> removing "+oldfilename)
            os.remove(build_dir+dir_sep+'textures'+dir_sep+oldfilename)
    if clean_tmp_files==True:
        clean_temporary_files(build_dir,['POLY','ELE'])                                                 
    else:
        clean_temporary_files(build_dir,['ELE'])
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-t3))+\
              'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
     # --> mth
    try:
        comp_func = application.comp_func.get()
        print('\n')
        shutdown=True
        if comp_func=='Exit program':
            for i in range(0, shutdown_timer-1):
                if application.red_flag.get()==1:
                    shutdown=False
                    print('\nExit timer interrupted.')
                    break;
                if i % shutd_msg_interval == 0:
                    print('Closing program in '+str(shutdown_timer-i)+' seconds ...')
                time.sleep(1)
            if shutdown==True:
                print('\nClosing program now ...')
                application.quit()
        elif comp_func=='Shutdown computer':
            for i in range(0, shutdown_timer-1):
                if application.red_flag.get()==1:
                    shutdown=False
                    print('\nShutdown timer interrupted.')
                    break;
                if i % shutd_msg_interval == 0:
                    print('Shutting down computer in '+str(shutdown_timer-i)+' seconds ...')
                time.sleep(1)
            if shutdown==True:
                print('\nShutting down computer now ...')
                os.system(shutdown_cmd)
    except:
        pass
    # <-- mth
    return
##############################################################################


##############################################################################
def build_overlay(lat,lon,file_to_sniff):
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
    strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
    t_ov=time.time()
    file_to_sniff_loc=Ortho4XP_dir+dir_sep+"tmp"+dir_sep+strlat+strlon+'.dsf'
    print("-> Making a copy of the original overlay DSF in tmp dir")
    os.system(copy_cmd + '  "'+file_to_sniff+'" "'+file_to_sniff_loc+'"')
    file = open(file_to_sniff_loc,'rb')
    # Merci Pascal P. pour cette élégante solution !
    dsfid = file.read(2).decode('ascii')
    file.close()
    if dsfid == '7z':
        print("-> The original DSF is a 7z archive, uncompressing...")
        os.system(rename_cmd+'"'+file_to_sniff_loc+'" "'+file_to_sniff_loc+'.7z" '+\
              devnull_rdir)
        os.system(unzip_cmd+' e -o'+Ortho4XP_dir+dir_sep+'tmp'+' "'+\
              file_to_sniff_loc+'.7z"')
    if 'dar' in sys.platform:
        dsftool_cmd=Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"DSFTool.app "
    elif 'win' in sys.platform:
        dsftool_cmd=Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"DSFTool.exe "
    else:
        dsftool_cmd=Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"DSFTool "
    print("-> Converting the copy to text format")
    dsfconvertcmd=[dsftool_cmd.strip(),' -dsf2text '.strip(),file_to_sniff_loc,Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'tmp_dsf.txt']
    fingers_crossed=subprocess.Popen(dsfconvertcmd,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            print('     '+line.decode("utf-8")[:-1])
    print("-> Expurging the mesh and the beach polygons from the text DSF")
    f=open(Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'tmp_dsf.txt','r')
    g=open(Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'tmp_dsf_without_mesh.txt','w')
    line=f.readline()
    g.write('PROPERTY sim/overlay 1\n')
    while line!='':
        if 'PROPERTY' in line:
            g.write(line)
        elif 'TERRAIN_DEF' in line:
            pass
        elif 'POLYGON_DEF' in line:
            g.write(line)
        elif 'NETWORK_DEF' in line:
            g.write(line)
        elif 'BEGIN_POLYGON 0' in line:
            while 'END_POLYGON' not in line:
                line=f.readline()
        elif 'BEGIN_POLYGON' in line:
            while 'END_POLYGON' not in line:
                g.write(line)
                line=f.readline()
            g.write(line)
        elif 'BEGIN_SEGMENT' in line:
            while 'END_SEGMENT' not in line:
                g.write(line)
                line=f.readline()
            g.write(line)
        else:
            pass
        line=f.readline()
    f.close()
    g.close()
    print("-> Converting back the text DSF to binary format")
    dsfconvertcmd=[dsftool_cmd.strip(),' -text2dsf '.strip(),Ortho4XP_dir+dir_sep+\
              'tmp'+dir_sep+'tmp_dsf_without_mesh.txt',Ortho4XP_dir+\
              dir_sep+'tmp'+dir_sep+'tmp_dsf_without_mesh.dsf'] 
    fingers_crossed=subprocess.Popen(dsfconvertcmd,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            print('     '+line.decode("utf-8")[:-1])
    dest_dir=Ortho4XP_dir+dir_sep+'yOrtho4XP_Overlays'+dir_sep+'Earth nav data'+dir_sep+\
            strlatround+strlonround
    print("-> Coping the final overlay DSF in "+dest_dir) 
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    os.system(copy_cmd+' "'+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'tmp_dsf_without_mesh.dsf" '+\
              ' "'+dest_dir+dir_sep+strlat+strlon+'.dsf"')
    os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'*.dsf' +devnull_rdir)
    os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'*.txt' +devnull_rdir)
    os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'*.raw' +devnull_rdir)
    if dsfid == '7z':
        os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'*.7z' +devnull_rdir)
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-t_ov))+\
              'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
    return
##############################################################################


##############################################################################
def build_masks(lat,lon,build_dir,mesh_filename_list):
    t4=time.time()
    try:
        application.red_flag.set(0)
    except:
        pass
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    eps=0.000001
    [til_x_min,til_y_min]=wgs84_to_texture(lat+1-eps,lon+eps,14,'BI')
    [til_x_max,til_y_max]=wgs84_to_texture(lat+eps,lon+1-eps,14,'BI')
    nx=(til_x_max-til_x_min)//16+1
    ny=(til_y_max-til_y_min)//16+1
    masks_im=Image.new("1",(nx*4096,ny*4096))
    masks_draw=ImageDraw.Draw(masks_im)
    
    masks_dir=Ortho4XP_dir+dir_sep+"Masks"+dir_sep+strlat+strlon
    if not os.path.exists(masks_dir):
        os.makedirs(masks_dir)
    if not os.path.isfile(masks_dir+dir_sep+'whole_tile.png') or keep_old_pre_mask==False:
        for mesh_filename in mesh_filename_list:
            try:
                f_mesh=open(mesh_filename,"r")
            except:
                continue
            for i in range(0,4):
                f_mesh.readline()
            nbr_pt_in=int(f_mesh.readline())
            pt_in=numpy.zeros(5*nbr_pt_in,'float')
            for i in range(0,nbr_pt_in):
                tmplist=f_mesh.readline().split()
                pt_in[5*i]=float(tmplist[0])
                pt_in[5*i+1]=float(tmplist[1])
                pt_in[5*i+2]=float(tmplist[2])
            for i in range(0,3):
                f_mesh.readline()
            for i in range(0,nbr_pt_in):
                tmplist=f_mesh.readline().split()
                pt_in[5*i+3]=float(tmplist[0])
                pt_in[5*i+4]=float(tmplist[1])
            for i in range(0,2): # skip 2 lines
                f_mesh.readline()
            nbr_tri_in=int(f_mesh.readline()) # read nbr of tris
            step_stones=nbr_tri_in//100
            percent=-1
            print(" Constructing binary mask for sea water / ground from mesh file "+str(mesh_filename))
            for i in range(0,nbr_tri_in):
                if i%step_stones==0:
                    percent+=1
                    try:
                        application.progress_attr.set(int(percent*5/10))
                        if application.red_flag.get()==1:
                            print("Masks construction process interrupted.")
                            return
                    except:
                        pass
                tmplist=f_mesh.readline().split()
                # look for the texture that will possibly cover the tri
                n1=int(tmplist[0])-1
                n2=int(tmplist[1])-1
                n3=int(tmplist[2])-1
                tri_type=tmplist[3] 
                if (tri_type in ['2','3']) or (tri_type=='1' and use_masks_for_inland==True):
                    continue
                # The next would be best to mask rivers as well
                #if (tri_type in ['1','2','3']):
                #    continue
                [lon1,lat1]=pt_in[5*n1:5*n1+2]
                [lon2,lat2]=pt_in[5*n2:5*n2+2]
                [lon3,lat3]=pt_in[5*n3:5*n3+2]
                bary_lat=(lat1+lat2+lat3)/3
                bary_lon=(lon1+lon2+lon3)/3
                [til_x,til_y]=wgs84_to_texture(bary_lat,bary_lon,14,'BI')
                nxloc=(til_x-til_x_min)//16
                nyloc=(til_y-til_y_min)//16
                [s1,t1]=st_coord(lat1,lon1,til_x,til_y,14,'BI')
                [s2,t2]=st_coord(lat2,lon2,til_x,til_y,14,'BI')
                [s3,t3]=st_coord(lat3,lon3,til_x,til_y,14,'BI')
                [px1,py1]=[nxloc*4096+int(s1*4096),nyloc*4096+int((1-t1)*4096)]
                [px2,py2]=[nxloc*4096+int(s2*4096),nyloc*4096+int((1-t2)*4096)]
                [px3,py3]=[nxloc*4096+int(s3*4096),nyloc*4096+int((1-t3)*4096)]
                try:
                    masks_draw.polygon([(px1,py1),(px2,py2),(px3,py3)],fill='white')
                except:
                    pass
            f_mesh.close()
    masks_im.save(masks_dir+dir_sep+'whole_tile.png')
    del(masks_im)
    if not use_gimp:
        print(" Blur of size masks_width applied to the binary mask...")		
        masks_im=Image.open(masks_dir+dir_sep+'whole_tile.png').convert("L")
        img_array=numpy.array(masks_im,dtype=numpy.uint8)
        #kernel=numpy.ones(int(masks_width))/int(masks_width)
        kernel=numpy.array(range(1,2*masks_width))
        kernel[masks_width:]=range(masks_width-1,0,-1)
        kernel=kernel/masks_width**2
        for i in range(0,len(img_array)):
            img_array[i]=numpy.convolve(img_array[i],kernel,'same')
        img_array=img_array.transpose() 
        for i in range(0,len(img_array)):
            img_array[i]=numpy.convolve(img_array[i],kernel,'same')
        img_array=img_array.transpose()
        img_array=2*numpy.minimum(img_array,127) #*numpy.ones(img_array.shape)) 
        img_array=numpy.array(img_array,dtype=numpy.uint8)
        masks_im=Image.fromarray(img_array)
        masks_im.save(masks_dir+dir_sep+'whole_tile_blured.png')
    else: #use_gimp
        print(" Gaussian blur and level adjustment applied to the binary mask with Gimp...")
        if ('dar' in sys.platform) or ('win' not in sys.platform):   # Mac and Linux
            os.system(gimp_cmd+" -i -c -b '(blurX "+' "'+masks_dir+dir_sep+\
                'whole_tile.png" '+str(masks_width)+' "'+masks_dir+dir_sep+\
                'whole_tile_blured.png")'+"' -b '(gimp-quit 0)' ")
        else: # Windows specific
            tmpf=open('batchgimp.bat','w')
            tmpcmd='"'+gimp_cmd+'" '+\
                   '-i -c -b "(blurX \\\"'+Ortho4XP_dir+'\\\\Masks\\\\'+strlat+strlon+'\\\\whole_tile.png\\\" '+\
                   str(masks_width)+' \\\"'+Ortho4XP_dir+'\\\\Masks\\\\'+strlat+strlon+'\\\\whole_tile_blured.png\\\")"'+\
                   ' -b "(gimp-quit 0)"'
            tmpf.write(tmpcmd)
            tmpf.close()
            os.system('batchgimp.bat')
            os.system(delete_cmd+' batchgimp.bat')
        try:
            masks_im=Image.open(masks_dir+dir_sep+'whole_tile_blured.png')
        except:
            print("\nGimp is either not present on your system, or didn't configure its")
            print("access command correctly, or it has no access to the blurX script-fu.")
            print("Check in the manual for testing instructions.")
            print("\nFailure.")
            print('_____________________________________________________________'+\
            '____________________________________')
            try:
                application.progress_attr.set(0)
            except:
                pass
            return
    try:
        application.progress_attr.set(90)
        if application.red_flag.get()==1:
            print("Masks construction process interrupted.")
            return
    except:
        pass
    print(" Purging old masks files if needed.") 
    for oldmaskfile in os.listdir(masks_dir):
        if 'tile' in oldmaskfile:
            continue
        else:
            os.remove(masks_dir+dir_sep+oldmaskfile)
    print(" Spitting tile mask into ZL14 based submasks and skipping black ones.")
    for nxloc in range(0,nx):
        for nyloc in range(0,ny):
            box=(nxloc*4096,nyloc*4096,(nxloc+1)*4096,(nyloc+1)*4096)
            tex_im=masks_im.crop(box)
            if tex_im.getextrema()[1]>=10:
                tex_im.save(masks_dir+dir_sep+str(til_y_min+nyloc*16)+'_'+str(til_x_min+nxloc*16)+'.png')
                #tex_im.save(build_dir+dir_sep+"textures"+dir_sep+str(til_y_min+nyloc*16)+'_'+str(til_x_min+nxloc*16)+'.png')
    try:
        application.progress_attr.set(100)
        if application.red_flag.get()==1:
            print("Masks construction process interrupted.")
            return
    except:
        pass
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-t4))+\
              'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
    return


##############################################################################
def build_tile_list(tile_list,build_dir_option,read_config,use_existing_mesh,bbmasks,bboverlays):
    global ortho_list,zone_list,default_website,default_zl 
    nbr_tiles=len(tile_list)
    default_website=application.map_choice.get()
    default_zl=application.zl_choice.get()
    n=1
    for tile in tile_list:
        [lat,lon]=tile
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if build_dir_option=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            if build_dir_option[-1]=='/':
                build_dir=build_dir_option[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
            else:
                build_dir=build_dir_option
        application.lat.set(lat)
        application.lon.set(lon)
        zone_list=[]
        ortho_list=[]
        if read_config:
            application.read_cfg()
        if not use_existing_mesh:
            print("\nTile "+str(n)+" / "+str(nbr_tiles))
            print("\nStep 1 : Building OSM and patch data for tile "+strlat+strlon+" : ")
            print("--------\n")
            build_poly_file(lat,lon,water_option,build_dir)
            if application.red_flag.get()==1:
                print("\nBatch build process interrupted.")
                print('_____________________________________________________________'+\
                      '____________________________________')
                return
            print("\nTile "+str(n)+" / "+str(nbr_tiles))
            print("\nStep 2 : Building mesh for tile "+strlat+strlon+" : ")
            print("--------\n")
            build_mesh(lat,lon,build_dir)
            if application.red_flag.get()==1:
                print("\nBatch build process interrupted.")
                print('_____________________________________________________________'+\
                      '____________________________________')
                return
            mesh_filename = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
            if bbmasks:
                print("\nTile "+str(n)+" / "+str(nbr_tiles))
                print("\nStep 2.5 : Building masks for tile "+strlat+strlon+" : ")
                print("--------\n")
                if complex_masks==False:
                    mesh_filename_list=[mesh_filename]
                else:
                    mesh_filename_list=[]
                    for closelat in [lat-1,lat,lat+1]:
                        for closelon in [lon-1,lon,lon+1]:
                            strcloselat='{:+.0f}'.format(closelat).zfill(3)
                            strcloselon='{:+.0f}'.format(closelon).zfill(4)
                            closemesh_filename=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strcloselat+strcloselon+\
                                   dir_sep+'Data'+strcloselat+strcloselon+".mesh"
                            if os.path.isfile(closemesh_filename):
                                mesh_filename_list.append(closemesh_filename)
                build_masks(lat,lon,build_dir,mesh_filename_list)
            if application.red_flag.get()==1:
                print("\nBatch build process interrupted.")
                print('_____________________________________________________________'+\
                      '____________________________________')
                return
        ortho_list=zone_list[:]
        if default_website!='None':
            ortho_list.append([[lat,lon,lat,lon+1,lat+1,lon+1,lat+1,lon,lat,lon],\
                    str(default_zl),str(default_website)])
        mesh_filename = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
        if os.path.isfile(mesh_filename)!=True:
            print("The mesh of Tile "+strlat+strlon+" was not found, skipping that one...")
            continue
        application.write_cfg()
        print("\nTile "+str(n)+" / "+str(nbr_tiles))
        print("\nStep 3 : Building Tile "+strlat+strlon+" : ")
        print("--------\n")
        build_tile(lat,lon,build_dir,mesh_filename,clean_tmp_files)
        if application.red_flag.get()==1:
            print("\nBatch build process interrupted.")
            print('_____________________________________________________________'+\
                      '____________________________________')
            return
        if bboverlays:
            print("\nIndependent Step  : Building of an Overlay DSF from third party data : ")
            print("-------------------\n")
            base_sniff_dir=application.sniff_dir_entry.get()
            strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
            strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
            file_to_sniff=base_sniff_dir+dir_sep+"Earth nav data"+dir_sep+\
                      strlatround+strlonround+dir_sep+strlat+strlon+'.dsf'
            if not os.path.isfile(file_to_sniff):
                print('\nFailure : there is no file to sniff from at the indicated place.')
                print('_____________________________________________________________'+\
                 '____________________________________')
            else:
                build_overlay(lat,lon,file_to_sniff)
        n+=1

     # --> mth
    try:
        comp_func = application.comp_func.get()
        print('\n')
        shutdown=True
        if comp_func=='Exit program':
            for i in range(0, shutdown_timer-1):
                if application.red_flag.get()==1:
                    shutdown=False
                    print('\nExit timer interrupted.')
                    break;
                if i % shutd_msg_interval == 0:
                    print('Closing program in '+str(shutdown_timer-i)+' seconds ...')
                time.sleep(1)
            if shutdown==True:
                print('\nClosing program now ...')
                application.quit()
        elif comp_func=='Shutdown computer':
            for i in range(0, shutdown_timer-1):
                if application.red_flag.get()==1:
                    shutdown=False
                    print('\nShutdown timer interrupted.')
                    break;
                if i % shutd_msg_interval == 0:
                    print('Shutting down computer in '+str(shutdown_timer-i)+' seconds ...')
                time.sleep(1)
            if shutdown==True:
                print('\nShutting down computer now ...')
                os.system(shutdown_cmd)
    except:
        pass
    # <-- mth
    return
##############################################################################


##############################################################################
def point_in_polygon(point,polygon):
    '''
    This procedures determines wether the input point belongs to the 
    polygon. The algorithm is based on the computation of the index 
    of the boundary of the polygon with respect to the point.
    A point is a list of 2 floats and a polygon is a list of 2N floats, N>=3,   
    and the first two floats equal the last two ones.  
    '''
    total_winding_nbr=0
    quadrants=[]
    for j in range(0,len(polygon)//2):
        if polygon[2*j] >= point[0]:
            if polygon[2*j+1] >= point[1]:
                quadrants.append(1)
            else:
                quadrants.append(4)
        else:
            if polygon[2*j+1] >= point[1]:
                quadrants.append(2)
            else:
                quadrants.append(3)
    winding_nbr=0
    for k in range(0,len(quadrants)-1):
        change=quadrants[k+1]-quadrants[k]
        if change in [1,-1,0]:
            winding_nbr += change
        elif change in [-3,3]:
            winding_nbr += (-1)*change/3
        elif change in [-2,2]:
            if (polygon[2*k]-point[0])*(polygon[2*k+3]-point[1])\
-(polygon[2*k+1]-point[1])*(polygon[2*k+2]-point[0])>=0:
                winding_nbr+=2
            else:
                winding_nbr+=-2
    change=quadrants[0]-quadrants[len(quadrants)-1]
    if change in [1,-1,0]:
        winding_nbr += change
    elif change in [-3,3]:
        winding_nbr += (-1)*change/3
    elif change in [-2,2]:
        if (polygon[2*len(quadrants)-2]-point[0])*(polygon[1]\
-point[1])-(polygon[2*len(quadrants)-1]-point[1])*(polygon[0]-point[0])>=0:
            winding_nbr+=2
        else:
            winding_nbr+=-2
    total_winding_nbr+=winding_nbr/4
    if total_winding_nbr == 0:
        return False
    else:
        return True
##############################################################################

##############################################################################
# distance squared from a point "point" to the line through "p1" et "p2"
##############################################################################
def point_to_line_distsquared(point,point1,point2):
    p0=point[0]-point1[0]
    p1=point[1]-point1[1]
    q0=point2[0]-point1[0]
    q1=point2[1]-point1[1]
    n2=q0**2+q1**2
    if n2<1e-12:
        return p0**2+p1**2
    return p0**2+p1**2-(p0*q0+p1*q1)**2/n2 
##############################################################################     



##############################################################################
def ramer_douglas_peucker(polygon,tol):
    dmax2=0
    cut=-1
    for i in range(1,len(polygon)-1):
       d2 = point_to_line_distsquared(polygon[i],polygon[0],polygon[-1])
       if d2 > dmax2:
           cut=i
           dmax2=d2
    if dmax2 > tol**2:
        r1=ramer_douglas_peucker(polygon[:cut+1],tol)
        r2=ramer_douglas_peucker(polygon[cut:],tol)
        return r1[:-1]+r2
    else:
        return [polygon[0],polygon[-1]]
##############################################################################    
         
        
##############################################################################
def clean_temporary_files(build_dir,steps):
    for step in steps:
        if step=='OSM':
            for f in os.listdir(build_dir):
                if 'OSM_' in f:
                    os.remove(os.path.join(build_dir,f))
        elif step=='POLY':
            for f in os.listdir(build_dir):
                if ('.poly' in f) or ('.apt' in f):
                    os.remove(os.path.join(build_dir,f))
        elif step=='ELE':
            for f in os.listdir(build_dir):
                if ('.ele' in f) or ('.node' in f) or ('.alt' in f):
                    os.remove(os.path.join(build_dir,f))
        elif step=='MESH':
            for f in os.listdir(build_dir):
                if ('.mesh' in f):
                    os.remove(os.path.join(build_dir,f))
    return
##############################################################################





##############################################################################
class Earth_Preview_window(Toplevel):
    
    dico_old_stuff={}
    earthzl=6 
    resolution=2**earthzl*256
    nx0=0
    ny0=0
    
    def __init__(self):
        Toplevel.__init__(self)
        self.title('Tiles collection')
        toplevel = self.winfo_toplevel()
        try:
        # On MS Windows one can set the "zoomed" state.
            toplevel.wm_state('zoomed')
        except:
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight() - 60
            geom_string = "%dx%d+0+0" % (w,h)
            toplevel.wm_geometry(geom_string) 
        self.columnconfigure(1,weight=1)
        self.rowconfigure(0,weight=1)
    
        # Constants/Variable
        self.dico_tiles_todo={}
        self.dico_tiles_done={}

        self.latlon         = StringVar()
        self.ptc            = IntVar()
        self.ptc.set(0)
        self.uem            = IntVar()
        self.uem.set(0)
        self.bbm            = IntVar()
        self.bbm.set(0)
        self.bbo            = IntVar()
        self.bbo.set(0)
 
    
        # Frames
        self.frame_left   =  Frame(self, border=4, relief=RIDGE,bg='light green')
        self.frame_right  =  Frame(self, border=4, relief=RIDGE,bg='light green')

        # Frames properties
        self.frame_right.rowconfigure(0,weight=1)
        self.frame_right.columnconfigure(0,weight=1)
    
        # Frames placement
        self.frame_left.grid(row=0,column=0,sticky=N+S+W+E)
        self.frame_right.grid(row=0,rowspan=60,column=1,sticky=N+S+W+E)

        # Widgets
        self.infotop        =  Label(self.frame_left,text="Four buttons below apply\nto active lat/lon only",bg="light green")
        self.deltile_btn      =  Button(self.frame_left,text='  Delete Tile   ',command=self.delete_tile)
        self.delosm_btn       =  Button(self.frame_left,text='  Delete OSM    ',command=self.delete_osm)
        self.delortho_btn     =  Button(self.frame_left,text='  Delete Ortho  ',command=self.delete_ortho)
        self.delall_btn       =  Button(self.frame_left,text='  Delete All    ',command=self.delete_all)
        self.infomid          =  Label(self.frame_left,text="---------------\nAll = OSM or Ortho or Tiles",bg="light green")
        self.toggle_old_btn   =  Button(self.frame_left,text='Toggle all stuff',command=self.toggle_old_stuff)
        self.infomid2         =  Label(self.frame_left,text="---------------\nBuild multiple tiles at once :",bg="light green")
        self.check1           =  Checkbutton(self.frame_left,text='Per tile config',anchor=W,\
                                   variable=self.ptc,bg="light green",activebackground="light green",highlightthickness=0)
        self.check2           =  Checkbutton(self.frame_left,text='Use existing mesh',anchor=W,\
                                   variable=self.uem,bg="light green",activebackground="light green",highlightthickness=0)
        self.check3           =  Checkbutton(self.frame_left,text='Build masks',anchor=W,\
                                   variable=self.bbm,bg="light green",activebackground="light green",highlightthickness=0)
        self.check4           =  Checkbutton(self.frame_left,text='Build overlays',anchor=W,\
                                   variable=self.bbo,bg="light green",activebackground="light green",highlightthickness=0)
        self.build_btn        =  Button(self.frame_left,text='  Batch Build   ',command=self.batch_build)
        self.refresh_btn      =  Button(self.frame_left,text='     Refresh    ',command=self.refresh)
        self.exit_btn         =  Button(self.frame_left,text='      Exit      ',command=self.destroy)
        self.shortcuts        =  Label(self.frame_left,text="Shortcuts :\n-------------------\nClick+hold=move map\nDouble-click=select active lat/lon\nShift+click=add for batch build\nR-click= link in Custom Scenery\n\nActive lat/lon\n---------------------",bg="light green")
        self.latlon_entry     =  Entry(self.frame_left,width=8,bg="white",fg="blue",textvariable=self.latlon)
        self.canvas           =  Canvas(self.frame_right,bd=0)

        # Placement of Widgets
        self.shortcuts.grid(row=13,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.latlon_entry.grid(row=14,column=0,padx=5,pady=5,sticky=N+S)
        self.infotop.grid(row=15,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.deltile_btn.grid(row=16,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.delosm_btn.grid(row=17,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.delortho_btn.grid(row=18,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.delall_btn.grid(row=19,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.infomid.grid(row=20,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.toggle_old_btn.grid(row=21,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.infomid2.grid(row=22,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.check1.grid(row=23,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.check2.grid(row=24,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.check3.grid(row=25,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.check4.grid(row=26,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.build_btn.grid(row=27,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.refresh_btn.grid(row=28,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.exit_btn.grid(row=29,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.canvas.grid(row=0,column=0,sticky=N+S+E+W)     
        
        self.init_canvas()
        self.refresh()
        
    def init_canvas(self):
        self.canvas.config(scrollregion=(1,1,2**self.earthzl*256-1,2**self.earthzl*256-1)) #self.canvas.bbox(ALL))
        self.canvas.xview_moveto(0.45)
        self.canvas.yview_moveto(0.3)
        x0=self.canvas.canvasx(0)
        y0=self.canvas.canvasy(0)
        self.nx0=int((8*x0)//self.resolution)
        self.ny0=int((8*y0)//self.resolution)
        self.canvas.bind("<ButtonPress-1>", self.scroll_start)
        self.canvas.bind("<B1-Motion>", self.scroll_move)
        self.canvas.bind("<Double-Button-1>",self.select_tile)
        self.canvas.bind("<Shift-ButtonPress-1>",self.add_tile)
        self.canvas.bind("<ButtonPress-3>",self.toggle_to_custom)
        self.canvas.focus_set()
        self.draw_canvas(self.nx0,self.ny0) 
        return
    
    def set_working_dir(self):
        if application.build_dir_entry.get()=='':
            self.working_dir=Ortho4XP_dir+dir_sep+'Tiles'
            self.working_type='legacy'
        else:
            self.working_dir=application.build_dir_entry.get()
            if self.working_dir[-1]=='/':
                self.working_dir=self.working_dir[:-1]
                self.working_type='legacy'
            else:
                self.working_type='onedir'

    def preview_existing_tiles(self):
        if not self.dico_tiles_done=={}:
            for tile in self.dico_tiles_done:
                self.canvas.delete(self.dico_tiles_done[tile])
            self.dico_tiles_done={}
        if self.working_type=='legacy':
            for dirname in os.listdir(self.working_dir):
                if "zOrtho4XP_" in dirname:
                    try:
                        strlat=dirname[-7:-4]
                        strlon=dirname[-4:]
                        lat=int(strlat)
                        lon=int(strlon)
                        strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
                        strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
                    except:
                        continue                     
                    [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
                    [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
                    if os.path.isfile(self.working_dir+dir_sep+dirname+dir_sep+"Earth nav data"+dir_sep+strlatround+strlonround+dir_sep+strlat+strlon+'.dsf'):
                        self.dico_tiles_done[str(lat)+'_'+str(lon)]=self.canvas.create_rectangle(x0,y0,x1,y1,fill='blue',stipple='gray12')
                        link=Custom_scenery_dir+dir_sep+custom_scenery_prefix+'zOrtho4XP_'+strlat+strlon
                        if os.path.isdir(link):
                            if os.path.samefile(os.path.realpath(link),os.path.realpath(self.working_dir+dir_sep+'zOrtho4XP_'+strlat+strlon)):
                                self.canvas.itemconfig(self.dico_tiles_done[str(lat)+'_'+str(lon)],stipple='gray50')
        elif self.working_type=='onedir':
            for dirname in os.listdir(self.working_dir+dir_sep+'Earth nav data'):
                for filename in os.listdir(self.working_dir+dir_sep+'Earth nav data'+dir_sep+dirname):
                    try:
                        lat=int(filename[0:3])   
                        lon=int(filename[3:7])
                    except:
                        continue
                    [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
                    [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
                    self.dico_tiles_done[str(lat)+'_'+str(lon)]=self.canvas.create_rectangle(x0,y0,x1,y1,fill='blue',stipple='gray12')
            link=Custom_scenery_dir+dir_sep+custom_scenery_prefix+'zOrtho4XP_'+os.path.basename(self.working_dir)
            if os.path.isdir(link):
                if os.path.samefile(os.path.realpath(link),os.path.realpath(self.working_dir)):
                    for tile in self.dico_tiles_done:
                        self.canvas.itemconfig(self.dico_tiles_done[tile],stipple='gray50')
        return

   
    def refresh(self):
        self.set_working_dir()
        self.preview_existing_tiles()
        return      

    def toggle_old_stuff(self):
        if not self.dico_old_stuff=={}:
            for tile in self.dico_old_stuff:
                self.canvas.delete(self.dico_old_stuff[tile])
            self.dico_old_stuff={}
            return    
        for dirname in os.listdir(self.working_dir): 
            if "zOrtho4XP_" in dirname:
                try:
                    strlat=dirname[-7:-4]
                    strlon=dirname[-4:]
                    lat=int(strlat)
                    lon=int(strlon)
                    strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
                    strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
                except:
                    continue                     
                [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
                [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
                if str(lat)+'_'+str(lon) not in self.dico_tiles_done:
                    self.dico_old_stuff[str(lat)+'_'+str(lon)]=self.canvas.create_rectangle(x0,y0,x1,y1,outline='red')
        for dirname in os.listdir(Ortho4XP_dir+dir_sep+"Orthophotos"):
            try:
                strlat=dirname[0:3]
                strlon=dirname[3:]
                lat=int(strlat)
                lon=int(strlon)
            except:
                continue
            [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
            [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
            if str(lat)+'_'+str(lon) not in self.dico_tiles_done and str(lat)+'_'+str(lon) not in self.dico_old_stuff:
               self.dico_old_stuff[str(lat)+'_'+str(lon)]=self.canvas.create_rectangle(x0,y0,x1,y1,outline='red')
        for dirname in os.listdir(Ortho4XP_dir+dir_sep+"OSM_data"):
            try:
                strlat=dirname[0:3]
                strlon=dirname[3:]
                lat=int(strlat)
                lon=int(strlon)
            except:
                continue
            [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
            [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
            if str(lat)+'_'+str(lon) not in self.dico_tiles_done and str(lat)+'_'+str(lon) not in self.dico_old_stuff:
               self.dico_old_stuff[str(lat)+'_'+str(lon)]=self.canvas.create_rectangle(x0,y0,x1,y1,outline='red')
        return  

    def delete_tile(self):
        if self.working_type=='legacy':
            try:
                strlat='{:+.0f}'.format(float(self.active_lat)).zfill(3)
                strlon='{:+.0f}'.format(float(self.active_lon)).zfill(4)
                shutil.rmtree(self.working_dir+dir_sep+"zOrtho4XP_"+strlat+strlon)
            except:
                pass
        elif self.working_type=='onedir':
            try:
                strlat='{:+.0f}'.format(float(self.active_lat)).zfill(3)
                strlon='{:+.0f}'.format(float(self.active_lon)).zfill(4)
                strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
                strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
                os.remove(self.working_dir+dir_sep+"Earth nav data"+dir_sep+strlatround+strlonround+dir_sep+strlat+strlon+'.dsf')
            except:
                pass
        self.preview_existing_tiles()
        self.toggle_old_stuff()
        self.toggle_old_stuff()
        return

    def delete_osm(self):
        try:
            strlat='{:+.0f}'.format(float(self.active_lat)).zfill(3)
            strlon='{:+.0f}'.format(float(self.active_lon)).zfill(4)
            shutil.rmtree(Ortho4XP_dir+dir_sep+"OSM_data"+dir_sep+strlat+strlon)
        except:
            pass
        self.preview_existing_tiles()
        self.toggle_old_stuff()
        self.toggle_old_stuff()
        return
    
    def delete_ortho(self):
        try:
            strlat='{:+.0f}'.format(float(self.active_lat)).zfill(3)
            strlon='{:+.0f}'.format(float(self.active_lon)).zfill(4)
            shutil.rmtree(Ortho4XP_dir+dir_sep+"Orthophotos"+dir_sep+strlat+strlon)
        except:
            pass
        self.preview_existing_tiles()
        self.toggle_old_stuff()
        self.toggle_old_stuff()
        return

    def delete_all(self):
        self.delete_tile()
        self.delete_osm()
        self.delete_ortho()
        return

         
    
    def select_tile(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        [lat,lon]=pix_to_wgs84(x,y,self.earthzl)
        lat=floor(lat)
        lon=floor(lon)
        self.active_lat=lat
        self.active_lon=lon
        strlat='{:+.0f}'.format(float(lat)).zfill(3)
        strlon='{:+.0f}'.format(float(lon)).zfill(4)
        self.latlon.set(strlat+strlon)        
        try:
            self.canvas.delete(self.active_tile)
        except:
            pass
        [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
        [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
        self.active_tile=self.canvas.create_rectangle(x0,y0,x1,y1,fill='',outline='yellow',width=3)
        #if str(lat)+'_'+str(lon) in self.dico_tiles_done:
        #    application.lat.set(lat)
        #    application.lon.set(lon)
        #    application.read_cfg()
        #else:
        #    application.lat.set(lat)
        #    application.lon.set(lon)
        #    application.zone_list=[]
        application.lat.set(lat)
        application.lon.set(lon)
        application.zone_list=[]
        return
    
    def toggle_to_custom(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        [lat,lon]=pix_to_wgs84(x,y,self.earthzl)
        lat=floor(lat)
        lon=floor(lon)
        strlat='{:+.0f}'.format(float(lat)).zfill(3)
        strlon='{:+.0f}'.format(float(lon)).zfill(4)
        if str(lat)+'_'+str(lon) not in self.dico_tiles_done:
            return
        if self.working_type=='legacy':
            link=Custom_scenery_dir+dir_sep+custom_scenery_prefix+'zOrtho4XP_'+strlat+strlon
            target=os.path.realpath(self.working_dir+dir_sep+'zOrtho4XP_'+strlat+strlon)
            if os.path.isdir(link):
                os.remove(link)
                self.preview_existing_tiles()
                return 
        elif self.working_type=='onedir': 
            link=Custom_scenery_dir+dir_sep+custom_scenery_prefix+'zOrtho4XP_'+os.path.basename(self.working_dir)
            target=os.path.realpath(self.working_dir)
            if os.path.isdir(link):
                os.remove(link)
                self.preview_existing_tiles()
                return 
        if ('dar' in sys.platform) or ('win' not in sys.platform): # Mac and Linux
            os.system("ln -s "+' "'+target+'" "'+link+'"')
        else:
            os.system('MKLINK /J "'+link+'" "'+target+'"')
        self.preview_existing_tiles()
        return 


    def add_tile(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        [lat,lon]=pix_to_wgs84(x,y,self.earthzl)
        lat=floor(lat)
        lon=floor(lon)
        if str(lat)+'_'+str(lon) not in self.dico_tiles_todo:
            #application.lat.set(lat)
            #application.lon.set(lon)
            [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
            [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
            self.dico_tiles_todo[str(lat)+'_'+str(lon)]=self.canvas.create_rectangle(x0,y0,x1,y1,fill='red',stipple='gray12') 
        else:
            self.canvas.delete(self.dico_tiles_todo[str(lat)+'_'+str(lon)]) 
            self.dico_tiles_todo.pop(str(lat)+'_'+str(lon),None)
        return

    def batch_build(self):
        tile_list=[]
        if self.ptc.get()==1:
            read_config=True
        else:
            read_config=False    
        if self.uem.get()==1:
            use_existing_mesh=True
        else:
            use_existing_mesh=False    
        if self.bbm.get()==1:
            bbmasks=True
        else:
            bbmasks=False    
        if self.bbo.get()==1:
            bboverlays=True
        else:
            bboverlays=False    
        for tile in self.dico_tiles_todo:
            [stlat,stlon]=tile.split('_')
            lat=int(stlat)
            lon=int(stlon)
            tile_list.append([lat,lon])
        application.build_tile_list_ifc(tile_list,read_config,use_existing_mesh,bbmasks,bboverlays) 
        return
    
    def batch_build_2(self):
        tile_list=[]
        for tile in self.dico_tiles_todo:
            [stlat,stlon]=tile.split('_')
            lat=int(stlat)
            lon=int(stlon)
            tile_list.append([lat,lon])
        application.build_tile_list_ifc(tile_list,read_config=True) 
        return

    def scroll_start(self,event):
        self.canvas.scan_mark(event.x, event.y)
        return

    def scroll_move(self,event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.redraw_canvas()
        return

    def redraw_canvas(self):
        x0=self.canvas.canvasx(0)
        y0=self.canvas.canvasy(0)
        nx0=int((8*x0)//self.resolution)
        ny0=int((8*y0)//self.resolution)
        if nx0==self.nx0 and ny0==self.ny0:
            return
        else:
           self.nx0=nx0
           self.ny0=ny0 
           self.canvas.delete(self.canv_imgNW)
           self.canvas.delete(self.canv_imgNE)
           self.canvas.delete(self.canv_imgSW)
           self.canvas.delete(self.canv_imgSE)
           #fargs_rc=[nx0,ny0]
           #self.rc_thread=threading.Thread(target=self.draw_canvas,args=fargs_rc)
           #self.rc_thread.start()
           self.draw_canvas(nx0,ny0)
           return 
      
    def draw_canvas(self,nx0,ny0):
           fileprefix=Ortho4XP_dir+dir_sep+"Previews"+dir_sep+"Earth"+dir_sep+"Earth2_ZL"+str(self.earthzl)+"_"
           filepreviewNW=fileprefix+str(nx0)+'_'+str(ny0)+".jpg"
           self.imageNW=Image.open(filepreviewNW)
           self.photoNW=ImageTk.PhotoImage(self.imageNW)
           self.canv_imgNW=self.canvas.create_image(nx0*2**self.earthzl*256/8,ny0*2**self.earthzl*256/8,anchor=NW,image=self.photoNW)
           self.canvas.tag_lower(self.canv_imgNW)
           if nx0<2**(self.earthzl-3)-1:
              filepreviewNE=fileprefix+str(nx0+1)+'_'+str(ny0)+".jpg"
              self.imageNE=Image.open(filepreviewNE)
              self.photoNE=ImageTk.PhotoImage(self.imageNE)
              self.canv_imgNE=self.canvas.create_image((nx0+1)*2**self.earthzl*256/8,ny0*2**self.earthzl*256/8,anchor=NW,image=self.photoNE)
              self.canvas.tag_lower(self.canv_imgNE)
           if ny0<2**(self.earthzl-3)-1:
              filepreviewSW=fileprefix+str(nx0)+'_'+str(ny0+1)+".jpg"
              self.imageSW=Image.open(filepreviewSW)
              self.photoSW=ImageTk.PhotoImage(self.imageSW)
              self.canv_imgSW=self.canvas.create_image(nx0*2**self.earthzl*256/8,(ny0+1)*2**self.earthzl*256/8,anchor=NW,image=self.photoSW)
              self.canvas.tag_lower(self.canv_imgSW)
           if nx0<2**(self.earthzl-3)-1 and ny0<2**(self.earthzl-3)-1:
              filepreviewSE=fileprefix+str(nx0+1)+'_'+str(ny0+1)+".jpg"
              self.imageSE=Image.open(filepreviewSE)
              self.photoSE=ImageTk.PhotoImage(self.imageSE)
              self.canv_imgSE=self.canvas.create_image((nx0+1)*2**self.earthzl*256/8,(ny0+1)*2**self.earthzl*256/8,anchor=NW,image=self.photoSE)
              self.canvas.tag_lower(self.canv_imgSE)
           return      
##############################################################################   



##############################################################################
class Preview_window(Toplevel):

    dico_color={15:'cyan',16:'green',17:'yellow',18:'orange',19:'red'}
    points=[]
    coords=[]
    polygon_list=[]
    polyobj_list=[]

    
    
    def __init__(self,lat,lon):
        self.points=[]
        self.coords=[]
        self.polygon_list=[]
        self.polyobj_list=[]
        Toplevel.__init__(self)
        self.title('Preview')
        toplevel = self.winfo_toplevel()
        try:
        # On MS Windows one can set the "zoomed" state.
            toplevel.wm_state('zoomed')
        except:
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight() - 60
            geom_string = "%dx%d+0+0" % (w,h)
            toplevel.wm_geometry(geom_string) 
        self.columnconfigure(1,weight=1)
        self.rowconfigure(0,weight=1)
    
        # Constants

        self.map_list        = px256_list
        self.map_list2       = px256_list+wms2048_list
        self.zl_list         = ['10','11','12','13']
    
        self.map_choice      = StringVar()
        self.map_choice.set('OSM')
        self.zl_choice=StringVar()
        self.zl_choice.set('11')
        self.progress_preview = IntVar()
        self.progress_preview.set(0)
        self.zmap_choice      = StringVar()
        if application.map_choice.get()!='None':
            self.zmap_choice.set(application.map_choice.get())
        else:
            self.zmap_choice.set('BI')

        self.zlpol=IntVar()
        self.zlpol.set(17)
        self.gb = StringVar()
        self.gb.set('0Gb')
    
        # Frames
        self.frame_left   =  Frame(self, border=4, relief=RIDGE,bg='light green')
        self.frame_right  =  Frame(self, border=4, relief=RIDGE,bg='light green')

        # Frames properties
        self.frame_right.rowconfigure(0,weight=1)
        self.frame_right.columnconfigure(0,weight=1)
    
        # Frames placement
        self.frame_left.grid(row=0,column=0,sticky=N+S+W+E)
        self.frame_right.grid(row=0,rowspan=60,column=1,sticky=N+S+W+E)

        # Widgets
        self.label_pp         =  Label(self.frame_left,anchor=W,text="Preview params ",\
                                 fg = "light green",bg = "dark green",\
                                 font = "Helvetica 16 bold italic")
        self.title_src        =  Label(self.frame_left,anchor=W,text="Source : ",bg="light green") 
        self.map_combo        =  ttk.Combobox(self.frame_left,textvariable=self.map_choice,\
                                 values=self.map_list,state='readonly',width=8)
        self.title_zl         =  Label(self.frame_left,anchor=W,text="Zoomlevel : ",bg="light green")
        self.zl_combo         =  ttk.Combobox(self.frame_left,textvariable=self.zl_choice,\
                                 values=self.zl_list,state='readonly',width=3)
        self.preview_btn      =  Button(self.frame_left, text='Preview',\
                                 command=lambda: self.preview_tile(lat,lon))
        self.pgbar_preview    =  ttk.Progressbar(self.frame_left,mode='determinate',\
                                 orient=HORIZONTAL,variable=self.progress_preview,)
        self.label_zp         =  Label(self.frame_left,anchor=W,text="Zone params ",\
                                 fg = "light green",bg = "dark green",\
                                 font = "Helvetica 16 bold italic")
        self.title_zsrc       =  Label(self.frame_left,anchor=W,text="Source : ",bg="light green") 
        self.zmap_combo       =  ttk.Combobox(self.frame_left,textvariable=self.zmap_choice,\
                                 values=self.map_list2,state='readonly',width=8)
        self.B15 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[15],\
                    activebackground=self.dico_color[15],selectcolor=self.dico_color[15],\
                    height=2,indicatoron=0,text='ZL15',variable=self.zlpol,value=15,\
                    command=self.redraw_poly)
        self.B16 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[16],\
                    activebackground=self.dico_color[16],selectcolor=self.dico_color[16],height=2,\
                    indicatoron=0,text='ZL16',variable=self.zlpol,value=16,command=self.redraw_poly)
        self.B17 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[17],\
                    activebackground=self.dico_color[17],selectcolor=self.dico_color[17],height=2,\
                    indicatoron=0,text='ZL17',variable=self.zlpol,value=17,command=self.redraw_poly)
        self.B18 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[18],\
                    activebackground=self.dico_color[18],selectcolor=self.dico_color[18],height=2,\
                    indicatoron=0,text='ZL18',variable=self.zlpol,value=18,command=self.redraw_poly)
        self.B19 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[19],\
                    activebackground=self.dico_color[19],selectcolor=self.dico_color[19],height=2,\
                    indicatoron=0,text='ZL19',variable=self.zlpol,value=19,command=self.redraw_poly)
        self.save_zone_btn    =  Button(self.frame_left,text='  Save zone  ',command=self.save_zone_cmd)
        self.del_zone_btn     =  Button(self.frame_left,text=' Delete zone ',command=self.delete_zone_cmd)
        self.save_zones_btn   =  Button(self.frame_left,text='Save and Exit',command=self.save_zone_list)
        self.load_poly_btn    =  Button(self.frame_left,text='  Load Poly  ',command=lambda: self.load_poly(lat,lon))
        self.exit_btn         =  Button(self.frame_left,text='   Abandon   ',command=self.destroy)
        self.title_gbsize     =  Label(self.frame_left,anchor=W,text="Approx. Add. Size : ",bg="light green") 
        self.gbsize           =  Entry(self.frame_left,width=6,bg="white",fg="blue",textvariable=self.gb)
        self.shortcuts        =  Label(self.frame_left,text="\nShift+click to add polygons",bg="light green")
        self.canvas           =  Canvas(self.frame_right,bd=0)

        # Placement of Widgets
        self.label_pp.grid(row=0,column=0,sticky=W+E)
        self.title_src.grid(row=1,column=0,sticky=W,padx=5,pady=5)
        self.map_combo.grid(row=1,column=0,padx=5,pady=5,sticky=E)
        self.title_zl.grid(row=2,column=0,sticky=W,padx=5,pady=5)
        self.zl_combo.grid(row=2,column=0,padx=5,pady=5,sticky=E)
        self.preview_btn.grid(row=5,column=0, padx=5, pady=0,sticky=N+S+W+E)
        self.pgbar_preview.grid(row=6,column=0, padx=5, pady=0,sticky=N+S+W+E)
        self.label_zp.grid(row=7,column=0,pady=10,sticky=W+E)
        self.title_zsrc.grid(row=8,column=0,sticky=W,padx=5,pady=10)
        self.zmap_combo.grid(row=8,column=0,padx=5,pady=10,sticky=E)
        self.B15.grid(row=10 ,column=0,padx=5,pady=0,sticky=N+S+E+W) 
        self.B16.grid(row=11,column=0,padx=5,pady=0,sticky=N+S+E+W) 
        self.B17.grid(row=12,column=0,padx=5,pady=0,sticky=N+S+E+W) 
        self.B18.grid(row=13,column=0,padx=5,pady=0,sticky=N+S+E+W) 
        self.B19.grid(row=14,column=0,padx=5,pady=0,sticky=N+S+E+W)
        self.title_gbsize.grid(row=15,column=0,padx=5,pady=10,sticky=W)
        self.gbsize.grid(row=15,column=0,padx=5,pady=10,sticky=E)
        self.save_zone_btn.grid(row=16,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.del_zone_btn.grid(row=17,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.load_poly_btn.grid(row=18,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.save_zones_btn.grid(row=19,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.exit_btn.grid(row=20,column=0,padx=5,pady=0,sticky=N+S+E+W)
        self.shortcuts.grid(row=21,column=0,padx=5,pady=0,sticky=N+S+E+W)
        self.canvas.grid(row=0,column=0,sticky=N+S+E+W)     
        
        
    def preview_tile(self,lat,lon):
        self.zoomlevel=int(self.zl_combo.get())
        zoomlevel=self.zoomlevel
        website=self.map_combo.get()    
        strlat='{:+.0f}'.format(float(lat)).zfill(3)
        strlon='{:+.0f}'.format(float(lon)).zfill(4)
        [tilxleft,tilytop]=wgs84_to_gtile(lat+1,lon,zoomlevel)
        [self.latmax,self.lonmin]=gtile_to_wgs84(tilxleft,tilytop,zoomlevel)
        [self.xmin,self.ymin]=wgs84_to_pix(self.latmax,self.lonmin,zoomlevel)
        [tilxright,tilybot]=wgs84_to_gtile(lat,lon+1,zoomlevel)
        [self.latmin,self.lonmax]=gtile_to_wgs84(tilxright+1,tilybot+1,zoomlevel)
        [self.xmax,self.ymax]=wgs84_to_pix(self.latmin,self.lonmax,zoomlevel)
        filepreview=Ortho4XP_dir+dir_sep+'Previews'+dir_sep+strlat+strlon+\
                    "_"+website+str(zoomlevel)+".jpg"       
        if os.path.isfile(filepreview) != True:
            fargs_ctp=[int(lat),int(lon),int(zoomlevel),website]
            self.ctp_thread=threading.Thread(target=create_tile_preview,args=fargs_ctp)
            self.ctp_thread.start()
            fargs_dispp=[filepreview,lat,lon]
            dispp_thread=threading.Thread(target=self.show_tile_preview,args=fargs_dispp)
            dispp_thread.start()
        else:
            self.show_tile_preview(filepreview,lat,lon)
        return

    def show_tile_preview(self,filepreview,lat,lon):
        global zone_list
        for item in self.polyobj_list:
            try:
                self.canvas.delete(item)
            except:
                pass
        try:
            self.canvas.delete(self.img_map)
        except:
            pass
        try:
            self.canvas.delete(self.boundary)
        except:
            pass
        try:
            self.ctp_thread.join()
        except:
            pass
        self.image=Image.open(filepreview)
        self.photo=ImageTk.PhotoImage(self.image)
        self.map_x_res=self.photo.width()
        self.map_y_res=self.photo.height()
        self.img_map=self.canvas.create_image(0,0,anchor=NW,image=self.photo)
        self.canvas.config(scrollregion=self.canvas.bbox(ALL))
        self.canvas.bind("<ButtonPress-1>", self.scroll_start)
        self.canvas.bind("<B1-Motion>", self.scroll_move)
        self.canvas.bind("<Shift-ButtonPress-1>",self.newPoint) 
        self.canvas.focus_set()
        self.canvas.bind('p', self.newPoint)
        self.canvas.bind('d', self.delete_zone_cmd)
        self.canvas.bind('n', self.save_zone_cmd)
        self.canvas.bind('<BackSpace>', self.delLast)
        self.polygon_list=[]
        self.polyobj_list=[]
        self.poly_curr=[]
        bdpoints=[]
        for [latp,lonp] in [[lat,lon],[lat,lon+1],[lat+1,lon+1],[lat+1,lon]]:
                #x=(lonp-self.lonmin)/(self.lonmax-self.lonmin)*self.map_x_res
                #y=(self.latmax-latp)/(self.latmax-self.latmin)*self.map_y_res
                [x,y]=self.latlon_to_xy(latp,lonp,self.zoomlevel)
                bdpoints+=[int(x),int(y)]
        self.boundary=self.canvas.create_polygon(bdpoints,\
                           outline='black',fill='', width=2)
        for zone in zone_list:
            self.coords=zone[0][0:-2]
            self.zlpol.set(zone[1])
            self.zmap_combo.set(zone[2])
            self.points=[]
            for idxll in range(0,len(self.coords)//2):
                latp=self.coords[2*idxll]
                lonp=self.coords[2*idxll+1]
                #x=(lonp-self.lonmin)/(self.lonmax-self.lonmin)*self.map_x_res
                #y=(self.latmax-latp)/(self.latmax-self.latmin)*self.map_y_res
                [x,y]=self.latlon_to_xy(latp,lonp,self.zoomlevel)
                self.points+=[int(x),int(y)]
            self.redraw_poly()
            self.save_zone_cmd()
        return

    def scroll_start(self,event):
        self.canvas.scan_mark(event.x, event.y)
        return

    def scroll_move(self,event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        return


    def redraw_poly(self):
        try:
            self.canvas.delete(self.poly_curr)
        except:
            pass
        try:
            color=self.dico_color[self.zlpol.get()]
            self.poly_curr=self.canvas.create_polygon(self.points,\
                           outline=color,fill='', width=2)
        except:
            pass
        return

    def load_poly(self,lat,lon):
        poly_file=filedialog.askopenfilename()    
        self.lift()
        try:
            f=open(poly_file,'r')
        except:
            return
        f.readline()
        array=[]
        for line in f.readlines():
           if 'END' in line:
              break
           [lonp,latp]=line.split()
           lonp=float(lonp)
           latp=float(latp)
           latp=latp if latp > lat-0.001 else lat-0.001
           latp=latp if latp < lat+1.001 else lat+1.001
           lonp=lonp if lonp > lon-0.001 else lon-0.001
           lonp=lonp if lonp < lon+1.001 else lon+1.001
           array.append([float(latp),float(lonp)])
        new_array=ramer_douglas_peucker(array,tol=0.002)
        for point in new_array:
           self.coords+=[point[0],point[1]]
           self.points+=self.latlon_to_xy(point[0],point[1],self.zoomlevel)
        self.redraw_poly()
        return


    def newPoint(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        self.points+=[x,y]
        #latp=self.latmax-(y/self.map_y_res)*(self.latmax-self.latmin)
        #lonp=self.lonmin+(x/self.map_x_res)*(self.lonmax-self.lonmin)
        [latp,lonp]=self.xy_to_latlon(x,y,self.zoomlevel)
        self.coords+=[latp,lonp]
        self.redraw_poly()
        return

    def xy_to_latlon(self,x,y,zoomlevel):
        pix_x=x+self.xmin
        pix_y=y+self.ymin
        return pix_to_wgs84(pix_x,pix_y,zoomlevel)
        

    def latlon_to_xy(self,lat,lon,zoomlevel):
        [pix_x,pix_y]=wgs84_to_pix(lat,lon,zoomlevel)
        return [pix_x-self.xmin,pix_y-self.ymin]

    def delLast(self,event):
        self.points=self.points[0:-2]
        self.coords=self.coords[0:-2]
        self.redraw_poly()
        return
    
    def compute_size(self):
        total_size=0
        for polygon in self.polygon_list:
            polyp=polygon[0]+polygon[0][0:2]
            area=0
            x1=polyp[0]
            y1=polyp[1]
            for j in range(1,len(polyp)//2):
                x2=polyp[2*j]
                y2=polyp[2*j+1]
                area+=(x2-x1)*(y2+y1)
                x1=x2
                y1=y2
            total_size+=abs(area)/2*((40000*cos(pi/180*polygon[1][0])/2**(int(self.zl_combo.get())+8))**2)*2**(2*(int(polygon[2])-17))/1024
        self.gb.set('{:.1f}'.format(total_size)+"Gb")
        return

    def save_zone_cmd(self):
        if len(self.points)<6:
            return
        self.polyobj_list.append(self.poly_curr)
        self.polygon_list.append([self.points,self.coords,self.zlpol.get(),\
                                 self.zmap_combo.get()])
        self.compute_size()
        self.poly_curr=[]
        self.points=[]
        self.coords=[]
        return
    
    def delete_zone_cmd(self):
        try:
            self.canvas.delete(self.poly_curr)
            self.poly_curr=self.polyobj_list[-1]
            self.points=self.polygon_list[-1][0]
            self.coords=self.polygon_list[-1][1]
            self.zlpol.set(self.polygon_list[-1][2])
            self.zmap_combo.set(self.polygon_list[-1][3])
            self.polygon_list.pop(-1)
            self.polyobj_list.pop(-1)
            self.compute_size()
        except:
            self.points=[]
            self.coords=[]
        return
    
    def save_zone_list(self):
        global zone_list
        
        def zlkey(item):
            return item[2]
        ordered_list=sorted(self.polygon_list,key=zlkey,reverse=True)
        zone_list=[]
        for item in ordered_list:
            tmp=[]
            for pt in item[1]:
                tmp.append(float('{:.3f}'.format(float(pt))))
            for pt in item[1][0:2]:     # repeat first point for point_in_polygon algo
                tmp.append(float('{:.3f}'.format(float(pt))))
            zone_list.append([tmp,item[2],item[3]])
        self.destroy()    
        return
############################################################################################

############################################################################################
class Ortho4XP_Graphical(Tk):

    def __init__(self):
        
        Tk.__init__(self)
        self.title('Ortho4XP '+version)
        toplevel = self.winfo_toplevel()
        try:
            toplevel.wm_state('zoomed')
        except:
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight() - 60
            geom_string = "%dx%d+0+0" % (w,h)
            toplevel.wm_geometry(geom_string) 
        self.columnconfigure(1,weight=1)
        self.rowconfigure(0,weight=1)
        sys.stdout=self
        
        # Variables
        self.red_flag        = IntVar()
        self.red_flag.set(0)
        self.lat             = IntVar()
        self.lat.set(48)
        self.lon             = IntVar()
        self.lon.set(-6)
        self.bdc             = IntVar()
        self.bdc.set(0)
        self.bd              = StringVar()
        self.bd.set('')
        self.ma              = StringVar()
        self.ma.set('0.01')
        self.ct              = StringVar()
        self.ct.set('0.2')
        self.minangc         = IntVar()
        self.minangc.set(0)
        self.minang          = StringVar()
        self.minang.set('')
        self.cdc             = IntVar()
        self.cdc.set(0)
        self.cde             = StringVar()
        self.cde.set('')
        self.water_type      = IntVar()
        self.water_type.set(3)
        self.rw              = StringVar()
        self.rw.set('0.2')
        self.skipd           = IntVar()
        self.skipd.set(0)
        self.skipc           = IntVar()
        self.skipc.set(0)
        self.cleantmp        = IntVar()
        self.cleantmp.set(0)
        self.cleanddster     = IntVar()
        self.cleanddster.set(0)
        self.complexmasks     = IntVar()
        self.complexmasks.set(0)
        self.masksinland     = IntVar()
        self.masksinland.set(0)
        self.verbose         = IntVar()
        self.verbose.set(1)
        self.sniff           = IntVar()
        self.sniff.set(0)
        self.sniff_dir       = StringVar()
        self.sniff_dir.set('')
        self.mw              = IntVar()
        self.mw.set(32)
        self.zl_choice=StringVar()
        self.zl_choice.set('16')
        self.zlsea_choice=StringVar()
        self.zlsea_choice.set('')
        self.c_tms_r         = IntVar()
        self.c_tms_r.set(0)
        self.map_choice      = StringVar()
        self.map_choice.set('BI')
        self.seamap_choice      = StringVar()
        self.seamap_choice.set('')
        self.progress_attr   = IntVar()
        self.progress_attr.set(0)
        self.progress_down   = IntVar()
        self.progress_down.set(0)
        self.progress_mont   = IntVar()
        self.progress_mont.set(0)
        self.progress_conv   = IntVar()
        self.progress_conv.set(0)
        # --> mth
        self.comp_func       = StringVar()
        self.comp_func.set('Do nothing')
        # <-- mth

        # Constants
        self.map_list        = ['None']+px256_list+wms2048_list
        self.zl_list         = ['12','13','14','15','16','17','18','19']
        # --> mth
        self.comp_func_list  = ['Do nothing','Exit program','Shutdown computer']
        # <-- mth
        # Frames
        self.frame_left       =  Frame(self, border=4,\
                                 relief=RIDGE,bg='light green')
        self.frame_right      =  Frame(self, border=4,\
                                 relief=RIDGE,bg='light green')
        self.frame_rdbtn      =  Frame(self.frame_left,\
                                 border=0,padx=5,pady=5,bg="light green")
        self.frame_lastbtn    =  Frame(self.frame_left,\
                                 border=0,padx=5,pady=5,bg="light green")
        # Frames properties
        self.frame_right.rowconfigure(0,weight=1)
        self.frame_right.columnconfigure(0,weight=1)
        self.frame_lastbtn.columnconfigure(0,weight=1)
        self.frame_lastbtn.columnconfigure(1,weight=1)
        self.frame_lastbtn.columnconfigure(2,weight=1)
        self.frame_lastbtn.columnconfigure(3,weight=1)
        self.frame_lastbtn.rowconfigure(0,weight=1)
        # Frames placement
        self.frame_left.grid(row=0,column=0,sticky=N+S+W+E)
        self.frame_right.grid(row=0,rowspan=60,column=1,sticky=N+S+W+E)
        self.frame_rdbtn.grid(row=16,column=0,columnspan=3,sticky=N+S+E+W)
        # --> mth
        # --> original
        # self.frame_lastbtn.grid(row=21,column=0,columnspan=6,sticky=N+S+E+W)
        # <-- original
        self.frame_lastbtn.grid(row=23,column=0,columnspan=6,sticky=N+S+E+W)
        # <-- mth

        # Widgets style
        combostyle  = ttk.Style()
        combostyle.theme_create('combostyle', parent='alt',settings = {'TCombobox':\
             {'configure':{'selectbackground': 'white','selectforeground':'blue',\
              'fieldbackground': 'white','foreground': 'blue','background': 'white'}}})
        combostyle.theme_use('combostyle') 
        # Widgets
        self.earth_btn        =  Button(self.frame_left, text='Earth tile map',\
                                 command=self.earth_preview)
        self.label_tc         =  Label(self.frame_left,anchor=W,text="Tile coordinates",\
                                   fg = "light green",bg = "dark green",\
                                   font = "Helvetica 16 bold italic")
        self.title_lat        =  Label(self.frame_left,anchor=W,text='Latitude  :',\
                                   bg="light green")
        self.latitude         =  Entry(self.frame_left,width=4,bg="white",fg="blue",textvariable=self.lat)
        self.title_lon        =  Label(self.frame_left,anchor=W,text='  Longitude  :',\
                                   bg="light green")
        self.longitude        =  Entry(self.frame_left,width=4,bg="white",fg="blue",textvariable=self.lon)
        self.build_dir_check  =  Checkbutton(self.frame_left,text='Custom build_dir  :',anchor=W,\
                                   variable=self.bdc,command=self.choose_dir,bg="light green",\
                                   activebackground="light green",highlightthickness=0)
        self.build_dir_entry  =  Entry(self.frame_left,width=20,bg="white",fg="blue",textvariable=self.bd)
        self.label_zl         =  Label(self.frame_left,anchor=W,text="Provider and Zoomlevel",\
                                    fg = "light green",bg = "dark green",font = "Helvetica 16 bold italic")
        self.title_src        =  Label(self.frame_left,anchor=W,text="Base source  :",bg="light green") 
        self.map_combo        =  ttk.Combobox(self.frame_left,textvariable=self.map_choice,\
                                    values=self.map_list,state='readonly',width=6)
        self.title_zl         =  Label(self.frame_left,anchor=W,text="  Base zoomlevel  :",bg="light green")
        self.zl_combo         =  ttk.Combobox(self.frame_left,textvariable=self.zl_choice,\
                                    values=self.zl_list,state='readonly',width=3)
        self.title_seasrc     =  Label(self.frame_left,anchor=W,text="Sea source  :",bg="light green") 
        self.seamap_combo        =  ttk.Combobox(self.frame_left,textvariable=self.seamap_choice,\
                                    values=['']+self.map_list,state='readonly',width=6)
        self.title_zlsea         =  Label(self.frame_left,anchor=W,text="  Sea zoomlevel  :",bg="light green")
        self.zlsea_combo         =  ttk.Combobox(self.frame_left,textvariable=self.zlsea_choice,\
                                    values=self.zl_list,state='readonly',width=3)
        self.preview_btn      =  Button(self.frame_left, text='Choose custom zoomlevel',command=self.preview_tile)
        #self.title_water      =  Label(self.frame_left,anchor=W,text="Water type  :",bg="light green")
        #self.watertype1       =  Radiobutton(self.frame_left,variable=self.water_type,value=1,text="X-Plane only",\
                #                            border=0,bg="light green",activebackground="light green",highlightthickness=0,\
                #                    command=self.choose_wt)
        #self.watertype2       =  Radiobutton(self.frame_left,variable=self.water_type,value=2,text="Photoreal only",\
                #                           border=0,bg="light green",activebackground="light green",highlightthickness=0,\
                #                    command=self.choose_wt)
        #self.watertype3       =  Radiobutton(self.frame_left,variable=self.water_type,value=3,text="Mixed with transparency",\
                #                           border=0,bg="light green",activebackground="light green",highlightthickness=0,\
                #                    command=self.choose_wt)
        self.label_osm        =  Label(self.frame_left,justify=RIGHT,anchor=W,text="Build vector data (OSM/Patches)",\
                                   fg = "light green",bg = "dark green",font = "Helvetica 16 bold italic")
        self.title_min_area   =  Label(self.frame_left,text='Min_area  :',anchor=W,bg="light green")
        self.min_area         =  Entry(self.frame_left,width=5,bg="white",fg="blue",textvariable=self.ma)
        self.del_osm_btn      =  Button(self.frame_left,text='Purge OSM data',command=self.purge_osm)
        self.get_osm_btn      =  Button(self.frame_left,text='Step 1 : Build vector data',command=self.build_poly_ifc)
        self.label_bm         =  Label(self.frame_left,anchor=W,text="Build base mesh",\
                                   fg = "light green",bg = "dark green",font = "Helvetica 16 bold italic")
        self.title_curv_tol   =  Label(self.frame_left,text='Curv_tol  :',anchor=W,bg="light green")
        self.curv_tol         =  Entry(self.frame_left,width=5,bg="white",fg="blue",textvariable=self.ct)
        self.min_angle_check  =  Checkbutton(self.frame_left,text='Min_angle :',anchor=W,variable=self.minangc,
                                 command=self.choose_minang,bg="light green",activebackground="light green",\
                                         highlightthickness=0)
        self.min_angle        =  Entry(self.frame_left,width=4,bg="white",fg="blue",textvariable=self.minang)
        self.build_mesh_btn   =  Button(self.frame_left,text='Step 2 : Build base mesh',command=self.build_mesh_ifc)
        self.custom_dem_check =  Checkbutton(self.frame_left,text='Custom DEM file :',anchor=W,\
                                   variable=self.cdc,command=self.choose_dem,bg="light green",\
                                   activebackground="light green",highlightthickness=0)
        self.custom_dem_entry =  Entry(self.frame_left,width=20,bg="white",fg="blue",textvariable=self.cde)
        self.label_dsf        =  Label(self.frame_left,justify=RIGHT,anchor=W,text="Build Tile",\
                                    fg = "light green",bg = "dark green",font = "Helvetica 16 bold italic")
        self.skipdown_check   =  Checkbutton(self.frame_left,text="Skip downloads",\
                                    anchor=W,variable=self.skipd,command=self.set_skip_downloads,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.skipconv_check   =  Checkbutton(self.frame_left,text="Skip converts",\
                                    anchor=W,variable=self.skipc,command=self.set_skip_converts,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.verbose_check    =  Checkbutton(self.frame_left,text="Verbose output",\
                                    anchor=W,variable=self.verbose,command=self.set_verbose_output,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.cleantmp_check   =  Checkbutton(self.frame_left,text="Clean tmp files",\
                                    anchor=W,variable=self.cleantmp,command=self.set_cleantmp,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.cleanddster_check=  Checkbutton(self.frame_left,text="Clean unused dds/ter files",\
                                    anchor=W,variable=self.cleanddster,command=self.set_cleanddster,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.complexmasks_check   =  Checkbutton(self.frame_left,text="Complex masks",\
                                    anchor=W,variable=self.complexmasks,command=self.set_complexmasks,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.masksinland_check=  Checkbutton(self.frame_left,text="Use masks for inland",\
                                    anchor=W,variable=self.masksinland,command=self.set_masksinland,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.label_overlay        =  Label(self.frame_left,justify=RIGHT,anchor=W,text="Build Overlays",\
                                    fg = "light green",bg = "dark green",font = "Helvetica 16 bold italic")
        self.sniff_check      =  Checkbutton(self.frame_left,text="Custom overlay dir :",\
                                    anchor=W,variable=self.sniff,command=self.choose_sniff_dir,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.sniff_dir_entry  =  Entry(self.frame_left,width=30,bg="white",fg="blue",textvariable=self.sniff_dir)
        self.sniff_btn        =  Button(self.frame_left,text='(Build overlay)',command=self.build_overlay_ifc)
        self.check_response   =  Checkbutton(self.frame_left,text="Check against white textures ",\
                                    anchor=W,variable=self.c_tms_r,command=self.set_c_tms_r,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.build_tile_btn   =  Button(self.frame_left,text='Step 3 : Build Tile',command=self.build_tile_ifc)
        self.title_masks_width=  Label(self.frame_left,text='Masks_width :',anchor=W,bg="light green")
        self.masks_width_e    =  Entry(self.frame_left,width=5,bg="white",fg="blue",textvariable=self.mw)
        self.build_masks_btn  =  Button(self.frame_left,text='(Step 2.5 : Build Masks)',command=self.build_masks_ifc)
        self.title_ratio_water=  Label(self.frame_left,text='Ratio_water : ',bg="light green")
        self.ratio_water_entry=  Entry(self.frame_left,width=4,bg="white",fg="blue",textvariable=self.rw)
        self.read_cfg_btn     =  Button(self.frame_lastbtn,text='Read Config ',command=self.read_cfg)
        self.write_cfg_btn    =  Button(self.frame_lastbtn,text='Write Config',command=self.write_cfg)
        self.kill_proc_btn    =  Button(self.frame_lastbtn,text='Stop process',command=self.stop_process)
        self.exit_btn         =  Button(self.frame_lastbtn,text='    Exit    ',command=self.quit)
        self.title_progress_a =  Label(self.frame_left,anchor=W,text="DSF/Masks progress",bg="light green")
        self.progressbar_attr =  ttk.Progressbar(self.frame_left,mode='determinate',\
                                 orient=HORIZONTAL,variable=self.progress_attr,)
        self.title_progress_d =  Label(self.frame_left,anchor=W,text="Download progress",bg="light green")
        self.progressbar_down =  ttk.Progressbar(self.frame_left,mode='determinate',\
                                 orient=HORIZONTAL,variable=self.progress_down,)
        self.title_progress_m =  Label(self.frame_left,anchor=W,text="Montage progress",bg="light green")
        self.progressbar_mont =  ttk.Progressbar(self.frame_left,mode='determinate',\
                                 orient=HORIZONTAL,variable=self.progress_mont,)
        self.title_progress_c =  Label(self.frame_left,anchor=W,text="Convert progress",bg="light green")
        self.progressbar_conv =  ttk.Progressbar(self.frame_left,mode='determinate',\
                                 orient=HORIZONTAL,variable=self.progress_conv,)
        # --> mth
        self.title_comp_func  = Label(self.frame_left,anchor=W,text="On completion :",bg="light green")
        self.comp_func_combo  = ttk.Combobox(self.frame_left,textvariable=self.comp_func,\
                                    values=self.comp_func_list,state='readonly')
        # <-- mth
        self.std_out          =  Text(self.frame_right)
        # Placement of Widgets
        self.earth_btn.grid(row=0,column=0,columnspan=6,padx=5,pady=5,sticky=N+S+E+W)
        self.label_tc.grid(row=1,column=0,columnspan=6,sticky=W+E)
        self.title_lat.grid(row=2,column=0, padx=5, pady=5,sticky=E+W)
        self.latitude.grid(row=2,column=1, padx=5, pady=5,sticky=W)
        self.title_lon.grid(row=2,column=2, padx=5, pady=5,sticky=E+W) 
        self.longitude.grid(row=2,column=3, padx=5, pady=5,sticky=W)
        self.build_dir_check.grid(row=3,column=0,columnspan=2, pady=5,sticky=N+S+E+W) 
        self.build_dir_entry.grid(row=3,column=2,columnspan=4, padx=5, pady=5,sticky=W+E)
        self.label_zl.grid(row=4,column=0,columnspan=6,sticky=W+E)
        self.title_src.grid(row=5,column=0,sticky=E+W,padx=5,pady=5)
        self.map_combo.grid(row=5,column=1,padx=5,pady=5,sticky=W)
        self.title_zl.grid(row=5,column=2,sticky=N+S+E+W,padx=5,pady=5)
        self.zl_combo.grid(row=5,column=3,columnspan=1,padx=5,pady=5,sticky=W)
        self.title_seasrc.grid(row=6,column=0,sticky=E+W,padx=5,pady=5)
        self.seamap_combo.grid(row=6,column=1,padx=5,pady=5,sticky=W)
        self.title_zlsea.grid(row=6,column=2,sticky=N+S+E+W,padx=5,pady=5)
        self.zlsea_combo.grid(row=6,column=3,columnspan=1,padx=5,pady=5,sticky=W)
        self.preview_btn.grid(row=5,column=4, columnspan=2,padx=5, pady=5,sticky=N+S+W+E)
        #self.title_water.grid(row=5,column=0,columnspan=1, padx=5,pady=5,sticky=N+S+E+W)
        #self.watertype1.grid(row=5,column=1,columnspan=2, pady=5,sticky=N+S+W)
        #self.watertype2.grid(row=6,column=1,columnspan=2, pady=5,sticky=N+S+W)
        #self.watertype3.grid(row=7,column=1,columnspan=2, pady=5,sticky=N+S+W)
        self.label_osm.grid(row=7,column=0,columnspan=6,sticky=W+E)
        self.title_min_area.grid(row=8,column=0, padx=5, pady=5,sticky=W+E) 
        self.min_area.grid(row=8,column=1, padx=5, pady=5,sticky=W)
        self.del_osm_btn.grid(row=8,column=2, columnspan=2, pady=5,sticky=N+S+W)
        self.get_osm_btn.grid(row=8,column=4, columnspan=2,padx=5, pady=5,sticky=N+S+W+E)
        self.label_bm.grid(row=9,column=0,columnspan=6,sticky=W+E)
        self.title_curv_tol.grid(row=10,column=0, padx=5, pady=5,sticky=W+E) 
        self.curv_tol.grid(row=10,column=1, padx=5, pady=5,sticky=W)
        self.min_angle_check.grid(row=10,column=2, padx=5, pady=5,sticky=W)
        self.min_angle.grid(row=10,column=3, padx=5, pady=5,sticky=W)
        self.build_mesh_btn.grid(row=10,column=4, columnspan=2,padx=5, pady=5,sticky=N+S+W+E)
        self.custom_dem_check.grid(row=11,column=0,columnspan=2, padx=5, pady=5,sticky=W)
        self.custom_dem_entry.grid(row=11,column=2,columnspan=4, padx=5, pady=5,sticky=N+S+E+W)
        self.label_dsf.grid(row=12,column=0,columnspan=6,sticky=W+E)
        self.skipdown_check.grid(row=13,column=0,columnspan=2, pady=5,sticky=N+S+E+W)
        self.skipconv_check.grid(row=13,column=2,columnspan=1, pady=5,sticky=N+S+E+W)
        self.check_response.grid(row=13,column=3,columnspan=3,sticky=W)
        self.verbose_check.grid(row=14,column=0,columnspan=2, pady=5,sticky=N+S+W)
        self.cleantmp_check.grid(row=14,column=2,columnspan=1, pady=5,sticky=N+S+W)
        self.cleanddster_check.grid(row=14,column=3,columnspan=2, pady=5,sticky=N+S+W)
        self.complexmasks_check.grid(row=15,column=0,columnspan=2, pady=5,sticky=N+S+W)
        self.masksinland_check.grid(row=15,column=2,columnspan=1, pady=5,sticky=N+S+W)
        self.title_masks_width.grid(row=16,column=0, padx=5, pady=5,sticky=W+E) 
        self.masks_width_e.grid(row=16,column=1, padx=5, pady=5,sticky=W)
        self.title_ratio_water.grid(row=16,column=2,columnspan=1, padx=5, pady=5,sticky=W) 
        self.ratio_water_entry.grid(row=16,column=3, padx=5, pady=5,sticky=W)
        self.build_masks_btn.grid(row=16,column=4,columnspan=2,padx=5,pady=5,sticky=N+S+W+E)
        self.build_tile_btn.grid(row=17,rowspan=3,column=4,columnspan=2,padx=5,sticky=N+S+W+E)
        self.read_cfg_btn.grid(row=0,column=0,padx=5, pady=5,sticky=N+S+W+E)
        self.write_cfg_btn.grid(row=0,column=1,padx=5, pady=5,sticky=N+S+W+E)
        self.kill_proc_btn.grid(row=0,column=2,padx=5,pady=5,sticky=N+S+W+E)
        self.exit_btn.grid(row=0,column=3, padx=5, pady=5,sticky=N+S+W+E)
        self.title_progress_a.grid(row=17,column=0,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.progressbar_attr.grid(row=17,column=2,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.title_progress_d.grid(row=18,column=0,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.progressbar_down.grid(row=18,column=2,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        #self.title_progress_m.grid(row=20,column=0,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        #self.progressbar_mont.grid(row=20,column=2,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.title_progress_c.grid(row=19,column=0,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.progressbar_conv.grid(row=19,column=2,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        # --> mth
        self.title_comp_func.grid(row=20,column=0,columnspan=2,padx=5,pady=5,sticky=E+W)
        self.comp_func_combo.grid(row=20,column=2,columnspan=2,padx=5,pady=5,sticky=E+W)
        # <-- mth
        self.label_overlay.grid(row=21,column=0,columnspan=6,sticky=W+E)
        self.sniff_check.grid(row=22,column=0,columnspan=2, pady=5,sticky=N+S+E+W)
        self.sniff_dir_entry.grid(row=22,column=2,columnspan=3, padx=5, pady=5,sticky=N+S+E+W)
        self.sniff_btn.grid(row=22,column=5,columnspan=1, padx=5, pady=5,sticky=N+S+E+W)
        self.std_out.grid(row=0,column=0,padx=5,pady=5,sticky=N+S+E+W)
        # read default choices from config file 
        try:
            self.water_type.set(water_option)
            self.rw.set(ratio_water)
            self.ma.set(min_area)
            self.ct.set(curvature_tol)
            if no_small_angles==True:
                self.minangc.set(1)
                self.minang.set(smallest_angle)
            else:
                self.minangc.set(0)
                self.minang.set('')
            self.skipd.set(skip_downloads)
            self.skipc.set(skip_converts)
            self.cleantmp.set(clean_tmp_files)
            self.cleanddster.set(clean_unused_dds_and_ter_files)
            self.verbose.set(verbose_output)
            if check_tms_response==True:
                self.c_tms_r.set(1)
            else:
                self.c_tms_r.set(0)
            self.map_choice.set(default_website)
            self.zl_choice.set(default_zl)
            self.mw.set(masks_width)
            self.sniff_dir.set(default_sniff_dir)
            self.complexmasks.set(complex_masks)
            self.masksinland.set(use_masks_for_inland)
        except:
            print("\nWARNING : the main config file is incomplete or does not follow the syntax,")
            print("I could not initialize all the parameters to your wish.")
            print('_____________________________________________________________'+\
                '____________________________________')
        return 
        
    def write(self,text):
        if text=='' or text[-1]!='\r':
            self.std_out.insert(END,str(text))
            self.std_out.see(END)
        else:
            self.std_out.delete("end linestart", "end") 
            self.std_out.insert(END,str(text))
            self.std_out.see(END)
        return

    def flush(self):
        return
    
    def stop_process(self):
        application.red_flag.set(1)
        return

    def choose_dir(self):
        if self.bdc.get()==1:
            self.bd.set(filedialog.askdirectory())
        else:
            self.bd.set('')
        return 
    
    def choose_dem(self):
        if self.cdc.get()==1:
            self.cde.set(filedialog.askopenfilename())
        else:
            self.cde.set('')
        return 
    
    def choose_minang(self):
        if self.minangc.get()==1:
            self.minang.set('5')
        else:
            self.minang.set('')
        return
    
    def choose_sniff_dir(self):
        if self.sniff.get()==1:
            self.sniff_dir.set(filedialog.askdirectory())
        else:
            self.sniff_dir.set('')
        return 
    
    def choose_wt(self):
        if True:
        #if self.water_type.get()==3:
            self.rw.set('0.2')
        #else:
        #    self.rw.set('')
        return
    

    def read_cfg(self):
        global build_dir,water_option,ratio_water,min_area,curvature_tol,\
               no_small_angles,smallest_angle,default_website,default_zl,\
               skip_downloads,skip_converts,verbose_output,clean_tmp_files,\
               dds_or_png,check_tms_response,complex_masks,use_masks_for_inland,zone_list,sea_texture_params
        print("reading config")
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
            if build_dir[-1]=='/':
                build_dir=build_dir[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
        try:
            exec(open(build_dir+dir_sep+'Ortho4XP.cfg').read(),globals())
        except:
            print('\nFailure : the tile specific config file is not present or does follow the syntax.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return 
        try:
            self.water_type.set(water_option)
            self.rw.set(ratio_water)
            self.ma.set(min_area)
            self.ct.set(curvature_tol)
            if no_small_angles==True:
                self.minangc.set(1)
                self.minang.set(smallest_angle)
            else:
                self.minangc.set(0)
                self.minang.set('')
            self.skipd.set(skip_downloads)
            self.skipc.set(skip_converts)
            self.cleantmp.set(clean_tmp_files)
            self.cleanddster.set(clean_unused_dds_and_ter_files)
            self.complexmasks.set(complex_masks)
            self.masksinland.set(use_masks_for_inland)
            self.verbose.set(verbose_output)
            if check_tms_response==True:
                self.c_tms_r.set(1)
            else:
                self.c_tms_r.set(0)
            try:
                self.map_choice.set(default_website)
                if sea_texture_params==[]:
                    self.seamap_choice.set('')
                else:
                    self.seamap_choice.set(sea_texture_params[0])
            except:
                print("\nFailure : your default provider is no longer present in your address book.")
                print('_____________________________________________________________'+\
                   '____________________________________')
                return
            self.zl_choice.set(default_zl)
            if sea_texture_params==[]:
                self.zlsea_choice.set('')
            else:
                self.zlsea_choice.set(sea_texture_params[1])
            self.mw.set(masks_width)
        except:
            print("\nWARNING : the main config file is incomplete or does not follow the syntax,")
            print("I could not initialize all the parameters to your wish.")
            print('_____________________________________________________________'+\
                '____________________________________')
        return
      
    def write_cfg(self):
        global zone_list
        [lat,lon]=self.load_latlon()
        if lat=='error':
           return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
            if build_dir[-1]=='/':
                build_dir=build_dir[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
        if not os.path.exists(build_dir):
            os.makedirs(build_dir)
        try:
            fgen=open(Ortho4XP_dir+dir_sep+"Ortho4XP.cfg",'r')
            fbuild=open(build_dir+dir_sep+"Ortho4XP.cfg",'w')
            fbuild.write("# generated from the generic config file :\n")
        except:
            print("\nI could not read or write the config file.")
            print("Are you sure about the indicated build_dir directory ?")
            print("\n Failure.")
            print('_____________________________________________________________'+\
                '____________________________________')
            return
        for line in fgen.readlines():
            fbuild.write(line)
        fgen.close()
        fbuild.write("\n# generated from the interface :\n")
        if self.skipd.get()==0:
            fbuild.write("skip_downloads=False\n")
        else:
            fbuild.write("skip_downloads=True\n")
        if self.skipc.get()==0:
            fbuild.write("skip_converts=False\n")
        else:
            fbuild.write("skip_converts=True\n")
        if self.c_tms_r.get()==0:
            fbuild.write("check_tms_response=False\n")
        else:
            fbuild.write("check_tms_response=True\n")
        if self.verbose.get()==0:
            fbuild.write("verbose_output=False\n")
        else:
            fbuild.write("verbose_output=True\n")
        if self.cleantmp.get()==0:
            fbuild.write("clean_tmp_files=False\n")
        else:
            fbuild.write("clean_tmp_files=True\n")
        if self.cleanddster.get()==0:
            fbuild.write("clean_unused_dds_and_ter_files=False\n")
        else:
            fbuild.write("clean_unused_dds_and_ter_files=True\n")
        if self.complexmasks.get()==0:
            fbuild.write("complex_masks=False\n")
        else:
            fbuild.write("complex_masks=True\n")
        if self.masksinland.get()==0:
            fbuild.write("use_masks_for_inland=False\n")
        else:
            fbuild.write("use_masks_for_inland=True\n")
        fbuild.write("min_area="+str(min_area)+"\n")
        fbuild.write("curvature_tol="+str(curvature_tol)+"\n")
        if self.minangc.get()==0:
            fbuild.write("no_small_angles=False\n")
        else:
            fbuild.write("no_small_angles=True\n")
        if self.minangc.get()==1:
            fbuild.write("smallest_angle="+str(smallest_angle)+"\n")
        fbuild.write("default_website='"+str(self.map_choice.get())+"'\n") 
        fbuild.write("default_zl="+str(self.zl_choice.get())+"\n") 
        if sea_texture_params != []:
            fbuild.write("sea_texture_params=['"+str(self.seamap_choice.get())+"',"+str(self.zlsea_choice.get())+"]\n")
        else:
            fbuild.write("sea_texture_params=[]\n")
        fbuild.write("zone_list=[]\n")
        for zone in zone_list:
            fbuild.write("zone_list.append("+str(zone)+")\n")
        fbuild.write("water_option="+str(water_option)+"\n")
        if water_option==3:
            fbuild.write("ratio_water="+str(ratio_water)+"\n")
        fbuild.write("masks_width="+str(masks_width)+"\n")
        fbuild.close()
        return

    def load_latlon(self):
        try:
            lat=int(self.latitude.get())
            lon=int(self.longitude.get())
            if lat<-85 or lat>85 or lon<-180 or lon>180:
                print('\nFailure : latitude and/or longitude exceed limit.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return ['error','error']
        except:
            print('\nFailure : latitude and/or longitude wrongly encoded.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return ['error','error']
        return [lat,lon]
 
    def preview_tile(self):
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        self.preview_window=Preview_window(lat,lon) 
        return
    
    def earth_preview(self):
        self.earth_window=Earth_Preview_window()
        return
    
    def purge_osm(self):
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        osm_dir=Ortho4XP_dir+dir_sep+'OSM_data'+dir_sep+strlat+strlon
        try:
            shutil.rmtree(osm_dir)
        except:
            print('_____________________________________________________________'+\
            '____________________________________')
        return
    
    def build_poly_ifc(self):
        global build_dir, min_area
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        try:
            min_area=float(self.min_area.get())
        except:
            print('\nFailure : parameter min_area wrongly encoded.')
            print('_____________________________________________________________'+\
            '____________________________________')
            return
        if (min_area<0):
            print('\nFailure : parameter min_area exceeds limits.')
            print('_____________________________________________________________'+\
            '____________________________________')
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
            if build_dir[-1]=='/':
                build_dir=build_dir[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
        #water_option= self.water_type.get()
        print("\nStep 1 : Building OSM and patch data for tile "+strlat+strlon+" : ")
        print("--------\n")
        fargs_get_osm=[lat,lon,water_option,build_dir]
        build_dir_thread=threading.Thread(target=build_poly_file,args=fargs_get_osm)
        build_dir_thread.start()
        return

    def build_mesh_ifc(self):
        global build_dir,curvature_tol,no_small_angles,smallest_angle
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        try:
            curvature_tol=float(self.curv_tol.get())
            if curvature_tol < 0.01 or curvature_tol>100:
                print('\nFailure : curvature_tol exceeds limits.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
        except:
            print('\nFailure : curvature_tol wrongly encoded.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return
        if self.minangc.get()==0:
            no_small_angles=False
        else:
            no_small_angles=True
        if no_small_angles==True:
            try:
                smallest_angle=int(self.minang.get())
            except:
                print('\nFailure : minimum angle wrongly encoded.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
            if (smallest_angle<0) or (smallest_angle>30):
                print('\nFailure : minimum angle larger than 30° not allowed.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
            if build_dir[-1]=='/':
                build_dir=build_dir[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
        try:
            curvature_tol=float(self.curv_tol.get())
            if curvature_tol < 0.01 or curvature_tol>100:
                print('\nFailure : curvature_tol exceeds limits.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
        except:
            print('\nFailure : curvature_tol wrongly encoded.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return
        if self.minangc.get()==0:
            no_small_angles=False
        else:
            no_small_angles=True
        if no_small_angles==True:
            try:
                smallest_angle=int(self.minang.get())
            except:
                print('\nFailure : minimum angle wrongly encoded.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
            if (smallest_angle<0) or (smallest_angle>30):
                print('\nFailure : minimum angle larger than 30° not allowed.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
        print("\nStep 2 : Building mesh for tile "+strlat+strlon+" : ")
        print("--------\n")
        fargs_build_mesh=[lat,lon,build_dir]
        build_mesh_thread=threading.Thread(target=build_mesh,args=fargs_build_mesh)
        build_mesh_thread.start()
        return

    def build_overlay_ifc(self):
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
        strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
        base_sniff_dir=self.sniff_dir_entry.get()
        print("\nIndependent Step  : Building of an Overlay DSF from third party data : ")
        print("-------------------\n")
        file_to_sniff=base_sniff_dir+dir_sep+"Earth nav data"+dir_sep+\
                      strlatround+strlonround+dir_sep+strlat+strlon+'.dsf'
        if not os.path.isfile(file_to_sniff):
            print('\nFailure : there is no file to sniff from at the indicated place.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return 
        fargs_build_overlay=[lat,lon,file_to_sniff]
        build_overlay_thread=threading.Thread(target=build_overlay,args=fargs_build_overlay)
        build_overlay_thread.start()
        return 
    
    def build_tile_ifc(self):
        global lat,lon,build_dir,skip_downloads,skip_converts,verbose_output,\
                clean_tmp_files,dds_or_png,water_overlay,ratio_water,use_masks_for_inland,ortho_list,zone_list,sea_texture_params
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
            if build_dir[-1]=='/':
                build_dir=build_dir[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
        mesh_filename = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
        if os.path.isfile(mesh_filename)!=True:
            print("You must first construct the mesh !")
            return
        if self.water_type.get()==1:
            water_overlay=False
        else:
            water_overlay=True
            try:
                ratio_water=float(self.ratio_water_entry.get())
            except:
                print("The ratio_water parameter is wrongly encoded.")
                return
        self.set_cleantmp()
        website=self.map_choice.get()
        zoomlevel=self.zl_choice.get()
        if self.seamap_choice.get() != '': 
           sea_texture_params=[self.seamap_choice.get(),int(self.zlsea_choice.get())]
        else:
           sea_texture_params=[]
        ortho_list=zone_list[:]
        if website!='None':
            ortho_list.append([[lat,lon,lat,lon+1,lat+1,lon+1,lat+1,lon,lat,lon],\
                    str(zoomlevel),str(website)])
        self.write_cfg()
        print("\nStep 3 : Building Tile "+strlat+strlon+" : ")
        print("--------\n")
        fargs_build_tile=[lat,lon,build_dir,mesh_filename,clean_tmp_files]
        build_tile_thread=threading.Thread(target=build_tile,\
                args=fargs_build_tile)
        build_tile_thread.start()
        return
    
    def build_masks_ifc(self):
        global lat,lon,build_dir,water_overlay,masks_width,compex_masks
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
            if build_dir[-1]=='/':
                build_dir=build_dir[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
        try:
            masks_width=int(self.masks_width_e.get())
            if masks_width < 1 or masks_width>1048:
                print('\nFailure : masks_width off limits.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
        except:
            print('\nFailure : masks_width wrongly encoded.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return
        if not os.path.exists(build_dir+dir_sep+"textures"):
            os.makedirs(build_dir+dir_sep+"textures")
        mesh_filename = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
        if os.path.isfile(mesh_filename)!=True:
            print("You must first construct the mesh !")
            return
        print("\nStep 2.5 : Building Masks for Tile "+strlat+strlon+" : ")
        print("----------\n")
        if complex_masks==False:
            mesh_filename_list=[mesh_filename]
        else:
            mesh_filename_list=[]
            for closelat in [lat-1,lat,lat+1]:
                for closelon in [lon-1,lon,lon+1]:
                    strcloselat='{:+.0f}'.format(closelat).zfill(3)
                    strcloselon='{:+.0f}'.format(closelon).zfill(4)
                    closemesh_filename=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strcloselat+strcloselon+\
                                   dir_sep+'Data'+strcloselat+strcloselon+".mesh"
                    if os.path.isfile(closemesh_filename):
                        mesh_filename_list.append(closemesh_filename)
        fargs_build_masks=[lat,lon,build_dir,mesh_filename_list]
        build_masks_thread=threading.Thread(target=build_masks,\
                args=fargs_build_masks)
        build_masks_thread.start()
        return

    def build_tile_list_ifc(self,tile_list,read_config,use_existing_mesh,bbmasks,bboverlays):
        global skip_downloads,skip_converts,verbose_output,min_area,no_small_angles,smallest_angle,curvature_tol,\
                clean_tmp_files,dds_or_png,water_overlay,ratio_water,use_masks_for_inland,\
                sea_texture_params
        if self.water_type.get()==1:
            water_overlay=False
        else:
            water_overlay=True
            try:
                ratio_water=float(self.ratio_water_entry.get())
            except:
                print("The ratio_water parameter is wrongly encoded.")
                return
        try:
            min_area=float(self.min_area.get())
        except:
            print('\nFailure : parameter min_area wrongly encoded.')
            print('_____________________________________________________________'+\
            '____________________________________')
            return
        if (min_area<0):
            print('\nFailure : parameter min_area exceeds limits.')
            print('_____________________________________________________________'+\
            '____________________________________')
            return
        try:
            curvature_tol=float(self.curv_tol.get())
            if curvature_tol < 0.01 or curvature_tol>100:
                print('\nFailure : curvature_tol exceeds limits.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
        except:
            print('\nFailure : curvature_tol wrongly encoded.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return
        if self.minangc.get()==0:
            no_small_angles=False
        else:
            no_small_angles=True
        if no_small_angles==True:
            try:
                smallest_angle=int(self.minang.get())
            except:
                print('\nFailure : minimum angle wrongly encoded.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
            if (smallest_angle<0) or (smallest_angle>30):
                print('\nFailure : minimum angle larger than 30° not allowed.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
        if self.seamap_choice.get() != '': 
           sea_texture_params=[self.seamap_choice.get(),int(self.zlsea_choice.get())]
        else:
           sea_texture_params=[]
        build_dir_option=self.build_dir_entry.get()
        fargs_build_tile_list=[tile_list,build_dir_option,read_config,use_existing_mesh,bbmasks,bboverlays]
        build_tile_list_thread=threading.Thread(target=build_tile_list,\
                args=fargs_build_tile_list)
        build_tile_list_thread.start()
        return

    def set_skip_downloads(self):
        global skip_downloads,skip_converts
        if self.skipd.get()==1:
            self.skipc.set(1)
            skip_downloads=True
            skip_converts=True
        else:
            skip_downloads=False  
        return
    
    def set_skip_converts(self):
        global skip_downloads, skip_converts
        if self.skipc.get()==0:
            skip_converts=False
            if self.skipd.get()==1:
                self.skipc.set(1)
                skip_converts=True
        return
    
    def set_c_tms_r(self):
        global check_tms_response
        if self.c_tms_r.get()==0:
            check_tms_response=False
        else:
            check_tms_response=True
        return

    def set_verbose_output(self):
        global verbose_output 
        if self.verbose.get()==0:
            verbose_output=False
        else:
            verbose_output=True
        return
    
    def set_cleantmp(self):
        global clean_tmp_files
        if self.cleantmp.get()==0:
            clean_tmp_files=False
        else:
            clean_tmp_files=True
        return
    
    def set_cleanddster(self):
        global clean_unused_dds_and_ter_files
        if self.cleanddster.get()==0:
            clean_unused_dds_and_ter_files=False
        else:
            clean_unused_dds_and_ter_files=True
        return
    
    def set_complexmasks(self):
        global complex_masks
        if self.complexmasks.get()==0:
            complex_masks=False
        else:
            complex_masks=True
        return
    
    def set_masksinland(self):
        global use_masks_for_inland
        if self.masksinland.get()==0:
            use_masks_for_inland=False
        else:
            use_masks_for_inland=True
        return
    
    def kill_process(self):
        return

##############################################################################


##############################################################################
#                                                                            #
#   LE PROGRAMME CHEF, QUI DIRIGE TOUT MAIS QUI NE FAIT RIEN.                #
#                                                                            #
##############################################################################

if __name__ == '__main__':
    if len(sys.argv)==1: # switch to the graphical interface
        ortho_list=[]
        zone_list=[]
        exec(open(Ortho4XP_dir+dir_sep+'Ortho4XP.cfg').read())
        if not os.path.exists(Ortho4XP_dir+dir_sep+'OSM_data'):
            os.makedirs(Ortho4XP_dir+dir_sep+'OSM_data')
        if not os.path.exists(Ortho4XP_dir+dir_sep+'Tiles'):
            os.makedirs(Ortho4XP_dir+dir_sep+'Tiles')
        os.system(delete_cmd+" "+Ortho4XP_dir+dir_sep+"tmp"+dir_sep+"*.jpg "+devnull_rdir)
        os.system(delete_cmd+" "+Ortho4XP_dir+dir_sep+"tmp"+dir_sep+"*.png "+devnull_rdir)
        application = Ortho4XP_Graphical()
        application.mainloop()	    
        application.quit()
        sys.exit()
    # sequel is only concerned with command line (AND NOT UP TO DATE !!!) 
    tinit=time.time()
    ortho_list=[]
    zone_list=[]
    if len(sys.argv)<3:
        usage('command_line')
    exec(open(Ortho4XP_dir+dir_sep+'Ortho4XP.cfg').read())
    try:
        lat=int(sys.argv[1])
        lon=int(sys.argv[2])
    except:
        usage('command_line')
    if len(sys.argv)==4:
        try:
            exec(open(Ortho4XP_dir+dir_sep+sys.argv[3]).read())
        except:
            print("Could not read the custom config file, probably a syntax error")
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    if water_option in [2,3]:
        water_overlay=True
    else:
        water_overlay=False
    try:
        exec(open(Ortho4XP_dir+dir_sep+'Carnet_d_adresses.py').read())
    except:
        usage('adresses')
    if build_dir=="default":
        build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
    print("\nStep 1 : Building OSM and patch data for tile "+strlat+strlon+" : ")
    print("--------\n")
    build_poly_file(lat,lon,water_option,build_dir)
    print("\nStep 2 : Building mesh for tile "+strlat+strlon+" : ")
    print("--------\n")
    build_mesh(lat,lon,build_dir)
    print("\nStep 2.5 : Building Masks for Tile "+strlat+strlon+" : ")
    print("----------\n")
    mesh_filename = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
    if complex_masks==False:
        mesh_filename_list=[mesh_filename]
    else:
        mesh_filename_list=[]
        for closelat in [lat-1,lat,lat+1]:
            for closelon in [lon-1,lon,lon+1]:
                strcloselat='{:+.0f}'.format(closelat).zfill(3)
                strcloselon='{:+.0f}'.format(closelon).zfill(4)
                closemesh_filename=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strcloselat+strcloselon+\
                               dir_sep+'Data'+strcloselat+strcloselon+".mesh"
                if os.path.isfile(closemesh_filename):
                    mesh_filename_list.append(closemesh_filename)
    # [Thanks to Simheaven] fix for missing folder textures
    build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
    if not os.path.exists(build_dir+dir_sep+"textures"):
        os.makedirs(build_dir+dir_sep+"textures")
    build_masks(lat,lon,build_dir,mesh_filename_list)
    ortho_list=zone_list[:]
    if default_website!='None':
        ortho_list.append([[lat,lon,lat,lon+1,lat+1,lon+1,lat+1,lon,lat,lon],\
                    str(default_zl),str(default_website)])
    print("\nStep 3 : Building Tile "+strlat+strlon+" : ")
    print("--------\n")
    build_tile(lat,lon,build_dir,mesh_filename,clean_tmp_files)
    print('\nBon vol !')
##############################################################################
#                                                                            #
#                           THAT'S ALL FOLKS                                 #
#                                                                            #
##############################################################################





