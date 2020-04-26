# -*- coding: utf-8 -*-
# @Time    : 2020/03/17
# @Author  : yujiezhang125
# @FileName: osm_addonroads_canceloverlap.py
# @Description: Add siwei road data onto osm data
# @Description: Cancel the non-highway roads that are overlapped by highway

import arcpy
import pandas as pd

# set the path of siwei data
workdir = r'D:\cityDNA\Data\ChinaRoad_38city.gdb\\'
def seperate_highway_road(city):
    print city + ' seperate highway/road...'
    city_siwei = workdir + city
    city_siwei_highway = city + '_swhighway'
    city_siwei_road = city + '_swroad'
    arcpy.MakeFeatureLayer_management(city_siwei, 'city_siwei')
    arcpy.SelectLayerByAttribute_management('city_siwei', 'NEW_SELECTION',
                                            "rdClass LIKE 'rd00%' OR rdClass LIKE 'rd02%'")
    arcpy.CopyFeatures_management('city_siwei', city_siwei_highway)
    arcpy.SelectLayerByAttribute_management('city_siwei', 'SWITCH_SELECTION',
                                            "rdClass LIKE 'rd00%' OR rdClass LIKE 'rd02%'")
    arcpy.CopyFeatures_management('city_siwei', city_siwei_road)
    arcpy.Delete_management('city_siwei')


def addonroads(basemap, addonmap):
    """
    :param basemap: 以osm路网数据为基础
    :param addonmap: 将siwei路网数据进行添加
    :return: osm和siwei路网合并后的文件basemap + "_osm_add_siwei"
    """
    print basemap + ' addonroads... '
    # project to "Asia Alberts Lambert"
    out_coordinate_system = arcpy.SpatialReference(102012)
    arcpy.Project_management(addonmap, addonmap + "proj", out_coordinate_system)

    # create 20m buffer of basemap
    print basemap + ' create 50 meters buffer...'
    arcpy.Buffer_analysis(basemap, basemap + "50", "50 Meters")

    # addonmapproj INTERSECT basemap20
    print basemap + ' intersect...'
    arcpy.Intersect_analysis([basemap + '50', addonmap + 'proj'], addonmap + 'inter', "ONLY_FID")

    # dissolve same FID
    print basemap + ' dissolve field...'
    fields = arcpy.ListFields(addonmap + 'inter')
    dissolve_field = fields[3].name
    arcpy.Dissolve_management(addonmap + 'inter', addonmap + 'interdis', dissolve_field)

    # add field
    print basemap + ' add field...'
    arcpy.AddField_management(addonmap + "proj", "LengthAll", "DOUBLE")
    arcpy.AddField_management(addonmap + 'interdis', "LengthPart", "DOUBLE")

    # calculate geometry
    print basemap + ' calculate geometry...'
    arcpy.CalculateField_management(addonmap + "proj", "LengthAll", "!shape.length@meters!", "PYTHON_9.3")
    arcpy.CalculateField_management(addonmap + 'interdis', "LengthPart", "!shape.length@meters!", "PYTHON_9.3")

    # before join table, create new field, add index
    print basemap + ' create new field, add index...'
    arcpy.AddField_management(addonmap + "proj", "FIDid", "LONG")
    # add cursor
    fc = addonmap + "proj"
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
    arcpy.AddIndex_management(addonmap + "proj", "FIDid", "index", "UNIQUE", "ASCENDING")

    # join table and export the result as sddonmap+join.shp
    print basemap + ' join table...'
    arcpy.MakeFeatureLayer_management(addonmap + "proj", "tempLayer")
    print basemap + " finish MakeFeatureLayer"
    arcpy.AddJoin_management("tempLayer", "FIDid", addonmap + 'interdis', dissolve_field, "KEEP_COMMON")
    print basemap + " finish addjoin"
    arcpy.CopyFeatures_management("tempLayer", addonmap + "join")
    print basemap + " finish copy feature"
    arcpy.Delete_management('tempLayer')
    print basemap + " finish delete"

    # calculate the percent
    arcpy.AddField_management(addonmap + "join", "percent", "DOUBLE")
    print basemap + " finish addfield"

    print basemap + ' calculate percent...'
    fc2 = addonmap + "join"
    fieldAll = addonmap + "proj_LengthAll"
    fieldPart = addonmap + "interdis_LengthPart"
    target = "percent"
    cursor = arcpy.UpdateCursor(fc2)
    for row in cursor:
        # calculate percent field
        row.setValue(target, row.getValue(fieldPart) / row.getValue(fieldAll))
        cursor.updateRow(row)

    # extract Threshold value
    arcpy.MakeFeatureLayer_management(addonmap + "join", 'lyr')
    arcpy.SelectLayerByAttribute_management('lyr', 'NEW_SELECTION', '"percent" > 0.3')
    arcpy.CopyFeatures_management('lyr', addonmap + "_add")
    arcpy.Delete_management('lyr')

    # in "percent" > 0.3, record 'beijing_swhighwayinterdis_FID_beijing_swhighwayproj' and delete from '_road' file
    print addonmap + " record FID..."
    fc = addonmap + "_add"
    field1 = addonmap + "interdis_FID_" + addonmap + "proj"
    fid = []
    cursor = arcpy.UpdateCursor(fc)
    for row in cursor:
        fid.append(row.getValue(field1))
        cursor.updateRow(row)
    # Delete cursor and row objects
    del cursor, row
    print addonmap + " record FID finished!"

    # delete the fid records in cancelmap
    arcpy.MakeFeatureLayer_management(addonmap, 'lyr')
    arcpy.CopyFeatures_management('lyr', addonmap + "_deloverlap")
    arcpy.Delete_management('lyr')
    print addonmap + " deleteRow OBJECTID..."
    fc = addonmap + "_deloverlap"
    field1 = "OBJECTID"
    with arcpy.da.UpdateCursor(fc, field1) as cursor:
        for row in cursor:
            if row[0] in fid:
                cursor.deleteRow()
    del cursor, row
    print addonmap + " deleteRow OBJECTID finished!"

    # Merge basemap and addonmap
    print basemap + ' merge...'
    arcpy.Merge_management([basemap, addonmap + "_deloverlap"], basemap + "_osm_add_siwei")

    # Project to WGS84
    out_coordinate_system = arcpy.SpatialReference(4326)
    arcpy.Project_management(basemap + "_osm_add_siwei", basemap + "_osm_add_siwei_proj", out_coordinate_system)
    # save the final result of highway to a simple name and convenient path
    arcpy.MakeFeatureLayer_management(basemap + "_osm_add_siwei_proj", 'lyr')
    arcpy.CopyFeatures_management('lyr', basemap + "_osm_add_siwei")
    arcpy.Delete_management('lyr')
    print basemap + ' finished!'


# combine name and pathnamefield
def name_pathname(city):
    print city + "_highway combine name field..."
    fc = city + "_highway_osm_add_siwei"
    field1 = "name"
    field2 = "PathName"

    cursor = arcpy.UpdateCursor(fc)
    for row in cursor:
        # print type(row.getValue(field1))
        if row.getValue(field1) is None:
            if row.getValue(field2) != ' ' and row.getValue(field2) != 'None':
                row.setValue(field1, row.getValue(field2))
        cursor.updateRow(row)
    # Delete cursor and row objects
    del cursor, row
    print city + "_highway combine name field finished!"

    print city + "_road combine name field..."
    fc = city + "_road_osm_add_siwei"
    field1 = "name"
    field2 = "PathName"

    cursor = arcpy.UpdateCursor(fc)
    for row in cursor:
        if row.getValue(field1) is None:
            if row.getValue(field2) != ' ' and row.getValue(field2) is not None:
                row.setValue(field1, row.getValue(field2))
        cursor.updateRow(row)

    # Delete cursor and row objects
    del cursor, row
    print city + "_road combine name field finished!"


# combine fclass and rdclass field
def fclass_rdclass(city):
    print city + "_highway combine fclass field..."
    fc = city + "_highway_osm_add_siwei"
    field1 = "fclass"
    field2 = "rdClass"
    cursor = arcpy.UpdateCursor(fc)
    for row in cursor:
        if row.getValue(field1) is None:
            if row.getValue(field2) != ' ' and row.getValue(field2) is not None:
                row.setValue(field1, row.getValue(field2))
        cursor.updateRow(row)
    # Delete cursor and row objects
    del cursor, row
    print city + "_highway combine fclass field finished!"

    print city + "_road combine fclass field..."
    fc = city + "_road_osm_add_siwei"
    field1 = "fclass"
    field2 = "rdClass"
    cursor = arcpy.UpdateCursor(fc)
    for row in cursor:
        if row.getValue(field1) is None:
            if row.getValue(field2) != ' ' and row.getValue(field2) is not None:
                row.setValue(field1, row.getValue(field2))
        cursor.updateRow(row)
    # Delete cursor and row objects
    del cursor, row
    print city + "_road combine fclass field finished!"


# change rdxx to trunk...
def fclass_str(city):
    print city + "_highway change fclass to str..."
    fc = city + "_highway_osm_add_siwei"
    field1 = "fclass"
    cursor = arcpy.UpdateCursor(fc)
    for row in cursor:
        if row.getValue(field1) == '':
            row.setValue(field1, "motorway")
        elif row.getValue(field1) == 'rd00':
            row.setValue(field1, "trunk")
        elif row.getValue(field1) == 'rd01':
            row.setValue(field1, "trunk")
        elif row.getValue(field1) == 'rd02':
            row.setValue(field1, "trunk")
        elif row.getValue(field1) == 'rd03':
            row.setValue(field1, "primary")
        elif row.getValue(field1) == 'rd04':
            row.setValue(field1, "primary")
        elif row.getValue(field1) == 'rd05':
            row.setValue(field1, "secondary")
        cursor.updateRow(row)
    # Delete cursor and row objects
    del cursor, row
    print city + "_highway change fclass to str finished!"

    print city + "_road change fclass to str..."
    fc = city + "_road_osm_add_siwei"
    field1 = "fclass"
    cursor = arcpy.UpdateCursor(fc)
    for row in cursor:
        if row.getValue(field1) == '':
            row.setValue(field1, "residential")
        elif row.getValue(field1) == 'rd00':
            row.setValue(field1, "trunk")
        elif row.getValue(field1) == 'rd01':
            row.setValue(field1, "trunk")
        elif row.getValue(field1) == 'rd02':
            row.setValue(field1, "trunk")
        elif row.getValue(field1) == 'rd03':
            row.setValue(field1, "primary")
        elif row.getValue(field1) == 'rd04':
            row.setValue(field1, "primary")
        elif row.getValue(field1) == 'rd05':
            row.setValue(field1, "secondary")
        cursor.updateRow(row)
    # Delete cursor and row objects
    del cursor, row
    print city + "_highway change fclass to str finished!"


# change Notype to " "
def name_str(city):
    print city + "_highway name to str..."
    fc = city + "_highway_osm_add_siwei"
    field1 = "name"
    cursor = arcpy.UpdateCursor(fc)
    for row in cursor:
        if row.getValue(field1) is None:
            row.setValue(field1, " ")
        cursor.updateRow(row)
    # Delete cursor and row objects
    del cursor, row
    print city + "_highway name to str finished!"

    print city + "_road name to str..."
    fc = city + "_road_osm_add_siwei"
    field1 = "name"
    cursor = arcpy.UpdateCursor(fc)
    for row in cursor:
        if row.getValue(field1) is None:
            row.setValue(field1, " ")
        cursor.updateRow(row)
    # Delete cursor and row objects
    del cursor, row
    print city + "_road name to str finished!"


# only keep first 6 fields
def del_field(city):
    print city + '_highway delete fields...'
    names = arcpy.ListFields(city + "_highway_osm_add_siwei")
    colnum = []
    for i in range(6, len(names) - 1):
        colnum.append(i)
    dropfields = []
    for i in colnum:
        dropfields.append(names[i].name)

    arcpy.MakeFeatureLayer_management(city + "_highway_osm_add_siwei", 'lyr')
    arcpy.CopyFeatures_management('lyr', city + "_highway_addon")
    arcpy.Delete_management('lyr')

    arcpy.DeleteField_management(city + "_highway_addon", dropfields)
    print city + "_highway delete unused fields finished!"

    print city + "_road delete fields..."
    names = arcpy.ListFields(city + "_road_osm_add_siwei")
    colnum = []
    for i in range(6, len(names) - 1):
        colnum.append(i)
    dropfields = []
    for i in colnum:
        dropfields.append(names[i].name)

    arcpy.MakeFeatureLayer_management(city + "_road_osm_add_siwei", 'lyr')
    arcpy.CopyFeatures_management('lyr', city + "_road_addon")
    arcpy.Delete_management('lyr')

    arcpy.DeleteField_management(city + "_road_addon", dropfields)
    print city + "_road delete unused fields finished!"


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

citylist = pd.read_csv(r'D:\CityDNA\Data\addonroads\city.csv', engine='python')['Name_EN'].tolist()

arcpy.env.workspace = r'D:\CityDNA\Data\Simplification\codetest.gdb'
arcpy.env.overwriteOutput = True

# test
city = 'beijing'
basemap = city + "_highway"
addonmap = city + "_swhighway"

# addonroads
for city in citylist:
    seperate_highway_road(city)
    addonroads(city + "_highway", city + "_swhighway")
    addonroads(city + "_road", city + "_swroad")
    print city + ' finished!!!'

keeplist = []
# complete keeplist and delete unused files
for city in citylist:
    keeplist.append(city + "_highway")
    keeplist.append(city + "_swhighway")
    keeplist.append(city + "_road")
    keeplist.append(city + "_swroad")
    keeplist.append(city + "_highway" + "_osm_add_siwei")
    keeplist.append(city + "_road" + "_osm_add_siwei")

files = arcpy.ListFeatureClasses()
for fl in files:
    if fl not in keeplist:
        arcpy.Delete_management(fl)


# deal with attribute table
for city in citylist:
    name_pathname(city)
    fclass_rdclass(city)
    name_str(city)
    fclass_str(city)
    del_field(city)
    print city + ' finished!!!'

for city in citylist:
    basemap = city + "_highway_addon"
    cancelmap = city + "_road_addon"
    CancelOverlapRoads(basemap, cancelmap)
    print city + ' finished!!!'

keeplist = []
# complete keeplist and delete unused files
for city in citylist:
    keeplist.append(city + "_highway")
    keeplist.append(city + "_swhighway")
    keeplist.append(city + "_road")
    keeplist.append(city + "_swunhighway")
    keeplist.append(city + "_highway" + "_osm_add_siwei")
    keeplist.append(city + "_road" + "_osm_add_siwei")
    keeplist.append(city + "_highway_addon")
    keeplist.append(city + "_road_addon")
    keeplist.append(city + "_highway_add_road")


files = arcpy.ListFeatureClasses()
for fl in files:
    if fl not in keeplist:
        arcpy.Delete_management(fl)
