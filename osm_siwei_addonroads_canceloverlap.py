# -*- coding: utf-8 -*-
# @Time    : 2020/03/17
# @Author  : yujiezhang125
# @FileName: osm_siwei_addonroads_canceloverlap.py
# @Description: Add siwei road data onto osm data
# @Description: Cancel the non-highway roads that are overlapped by highway

import arcpy
import pandas as pd

arcpy.env.workspace = r'D:\CityDNA\Data\Simplification\codetest2.gdb'
arcpy.env.overwriteOutput = True

# simplified road data (simp_path should be same as 'arcpy.env.workspace' in osm_siwei_simplify_highway_road.py)
simp_path = r'D:\CityDNA\Data\Simplification\codetest1.gdb'

citylist = pd.read_csv(r'D:\CityDNA\Data\addonroads\city.csv', engine='python')['Name_EN'].tolist()


# canceloverlap and merge
def CancelOverlapRoads(basemap, cancelmap):
    print basemap + ' cancel overlap roads... '
    # project to "Asia Alberts Lambert"
    out_coordinate_system = arcpy.SpatialReference(102012)
    arcpy.Project_management(cancelmap, cancelmap + "proj", out_coordinate_system)

    # create 20m buffer of basemap
    print basemap + ' create 50 meters buffer...'
    arcpy.Buffer_analysis(basemap, basemap + "50", "50 Meters")

    # cancelmapproj INTERSECT basemap20
    print basemap + ' intersect...'
    arcpy.Intersect_analysis([basemap + '50', cancelmap + 'proj'], cancelmap + 'inter')

    # dissolve same FID !!!!NAME
    print basemap + ' dissolve field...'
    dissolve_field = "FID_" + cancelmap + 'proj'
    arcpy.Dissolve_management(cancelmap + 'inter', cancelmap + 'interdis', dissolve_field)

    # add field
    print basemap + ' add field...'
    arcpy.AddField_management(cancelmap + "proj", "LengthAll", "DOUBLE")
    arcpy.AddField_management(cancelmap + 'interdis', "LengthPart", "DOUBLE")

    # calculate geometry
    print basemap + ' calculate geometry...'
    arcpy.CalculateField_management(cancelmap + "proj", "LengthAll", "!shape.length@meters!", "PYTHON_9.3")
    arcpy.CalculateField_management(cancelmap + 'interdis', "LengthPart", "!shape.length@meters!", "PYTHON_9.3")

    # before join table, create new field, add index
    print basemap + ' create new field, add index...'
    arcpy.AddField_management(cancelmap + "proj", "FIDid", "LONG")
    # add cursor
    fc = cancelmap + "proj"
    field1 = "OBJECTID"
    field2 = "FIDid"
    cursor = arcpy.UpdateCursor(fc)
    for row in cursor:
        # field2(FIDid) will be equal to field1(FID)
        row.setValue(field2, row.getValue(field1))
        cursor.updateRow(row)
    del row
    del cursor
    # make index
    arcpy.AddIndex_management(cancelmap + "proj", "FIDid", "index", "UNIQUE", "ASCENDING")

    # join table and export the result as addonmap+join.shp
    print basemap + ' join table...'
    arcpy.MakeFeatureLayer_management(cancelmap + "proj", "tempLayer")
    arcpy.AddJoin_management("tempLayer", "FIDid", cancelmap + 'interdis', dissolve_field, "KEEP_COMMON")
    arcpy.CopyFeatures_management("tempLayer", cancelmap + "join")
    arcpy.Delete_management('tempLayer')

    # calculate the percent
    print basemap + " addfield..."
    arcpy.AddField_management(cancelmap + "join", "percent", "DOUBLE")

    print basemap + ' calculate percent...'
    fc2 = cancelmap + "join"
    fieldAll = cancelmap + "proj_LengthAll"
    fieldPart = cancelmap + "interdis_LengthPart"
    target = "percent"
    cursor = arcpy.UpdateCursor(fc2)
    for row in cursor:
        # calculate percent field
        row.setValue(target, row.getValue(fieldPart) / row.getValue(fieldAll))
        cursor.updateRow(row)
    del row
    del cursor

    # extract Threshold value
    arcpy.MakeFeatureLayer_management(cancelmap + "join", 'lyr')
    arcpy.SelectLayerByAttribute_management('lyr', 'NEW_SELECTION', '"percent" > 0.3')
    arcpy.CopyFeatures_management('lyr', cancelmap + "_add")
    arcpy.Delete_management('lyr')

    # in "percent" > 0.3, record 'beijing_road_addoninterdis_FID_beijing_road_addonproj' and delete from '_road' file
    print cancelmap + " record FID..."
    fc = cancelmap + "_add"
    field1 = city + "_road_addoninterdis_FID_" + city + "_road_addonproj"
    fid = []
    cursor = arcpy.UpdateCursor(fc)
    for row in cursor:
        fid.append(row.getValue(field1))
        cursor.updateRow(row)
    # Delete cursor and row objects
    del cursor, row
    print cancelmap + " record FID finished!"

    # delete the fid records in cancelmap
    arcpy.MakeFeatureLayer_management(cancelmap, 'lyr')
    arcpy.CopyFeatures_management('lyr', cancelmap + "_deloverlap")
    arcpy.Delete_management('lyr')
    print cancelmap + " deleteRow OBJECTID..."
    fc = cancelmap + "_deloverlap"
    field1 = "OBJECTID"
    with arcpy.da.UpdateCursor(fc, field1) as cursor:
        for row in cursor:
            if row[0] in fid:
                cursor.deleteRow()
    del cursor, row
    print cancelmap + " deleteRow OBJECTID finished!"

    # Merge basemap and cancelmap
    print basemap + ' merge...'
    arcpy.Merge_management([basemap, cancelmap + "_deloverlap"], city + "_highway_add_road")

    # Project to WGS84
    out_coordinate_system = arcpy.SpatialReference(4326)
    arcpy.Project_management(city + "_highway_add_road", city + "_highway_add_road_proj", out_coordinate_system)
    # save the final result of highway to a simple name and convenient path
    arcpy.MakeFeatureLayer_management(city + "_highway_add_road_proj", 'lyr')
    arcpy.CopyFeatures_management('lyr', city + "_highway_add_road")
    arcpy.Delete_management('lyr')
    print basemap + ' finished!'


# ===================================
'''
函数定义部分结束，以下为循环运行部分
'''

# import simplified road data to current work environment
for city in citylist:
    arcpy.MakeFeatureLayer_management(simp_path + "\\" + city + "_highway_addon", "tempLayer")
    arcpy.CopyFeatures_management("tempLayer", city + "_highway_addon")
    arcpy.Delete_management('tempLayer')

    arcpy.MakeFeatureLayer_management(simp_path + "\\" + city + "_road_addon", "tempLayer")
    arcpy.CopyFeatures_management("tempLayer", city + "_road_addon")
    arcpy.Delete_management('tempLayer')
    print city + " import simplified data finished!"


for city in citylist:
    basemap = city + "_highway_addon"
    cancelmap = city + "_road_addon"
    CancelOverlapRoads(basemap, cancelmap)
    print city + ' finished!!!'

keeplist = []
# complete keeplist and delete unused files
for city in citylist:
    keeplist.append(city + "_highway_addon")
    keeplist.append(city + "_road_addon")
    keeplist.append(city + "_highway_add_road")


files = arcpy.ListFeatureClasses()
for fl in files:
    if fl not in keeplist:
        arcpy.Delete_management(fl)
print "Finish delete files!!!"

