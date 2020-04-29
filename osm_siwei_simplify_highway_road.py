# -*- coding: utf-8 -*-
# @Time    : 2020/03/17
# @Author  : yujiezhang125
# @FileName: osm_siwei_simplify_highway_road.py
# @Description: Seperate osm highway and non-highway into two part.
# @Description: Simplify highway and non-highway, and merge multi-line roads to single-line roads

import arcpy
import pandas as pd

arcpy.env.workspace = r'D:\CityDNA\Data\Simplification\fourcity\fourcity\siwei_single_road.gdb'
arcpy.env.overwriteOutput = True

# read in osm data of whole country
china_osm2020 = r'D:\cityDNA\Data\Simplification\gis_osm_roads_free_1\gis_osm_roads_free_1.shp'
# read in 38 cities' boundary
clip_root = r'D:\CityDNA\Data\Simplification\fourcity\fourcity\bound.gdb'
# output path
workdir = arcpy.env.workspace + '\\'

# set the path of siwei data
siweidir = r'D:\cityDNA\Data\ChinaRoad_38city.gdb'

# read in citylist
citylist = pd.read_csv(r"D:\CityDNA\Data\Simplification\new33city\citylist_33city.csv", engine='python')['name'].tolist()


def clip_city_original_osm(city):
    """
    :param city: 待处理城市的名称（汉语拼音全拼 小写字母）
    :return: 返回当前城市的osm路网
    """
    print city + ' clipping...'
    boundary = clip_root + "\\" + city + '.shp'
    outpath = workdir + city
    arcpy.Clip_analysis(china_osm2020, boundary, outpath)


def name_ref(city):
    """
    :param city: 待处理城市的名称（汉语拼音全拼 小写字母）
    :return: 当文件name字段存在空值时，用ref字段的内容进行填充，返回当前城市的osm路网
    """
    print city + ' name_ref ing...'
    fc = workdir + city
    field1 = "name"
    field2 = "ref"
    cursor = arcpy.UpdateCursor(fc)
    for row in cursor:
        if row.getValue(field1).encode('utf-8') == ' ':
            row.setValue(field1, row.getValue(field2))
        cursor.updateRow(row)
    # Delete cursor and row objects
    del cursor, row


def seperate_highway_unhighway(city):
    """
    :param city: 待处理城市的名称（汉语拼音全拼 小写字母）
    :return: 分别返回当前城市osm路网的高速（city + 'highway'）和非高速（city + 'unhighway'）部分
    """
    print city + ' seperate highway/unhighway...'
    city_osm = workdir + city
    city_osm_highway = workdir + city + '_highway'
    city_osm_road = workdir + city + '_road'
    arcpy.MakeFeatureLayer_management(city_osm, 'city_osm')
    arcpy.SelectLayerByAttribute_management('city_osm', 'NEW_SELECTION',
                                            "fclass LIKE 'motorway%' OR fclass LIKE 'trunk%'")
    arcpy.CopyFeatures_management('city_osm', city_osm_highway)
    arcpy.SelectLayerByAttribute_management('city_osm', 'SWITCH_SELECTION',
                                            "fclass LIKE 'motorway%' OR fclass LIKE 'trunk%'")
    arcpy.CopyFeatures_management('city_osm', city_osm_road)
    arcpy.Delete_management('city_osm')


def unhighway_select(city):
    """
    :param city: 待处理城市的名称（汉语拼音全拼 小写字母）
    :return: 分别返回当前城市非高速路网筛选后的结果（city + '_unhighway_selected'）
    """
    print city + ' road select...'
    city_osm_road = workdir + city + '_road'
    city_osm_road_select = workdir + city + '_road_selected'
    arcpy.MakeFeatureLayer_management(city_osm_road, 'temp')
    expression = "fclass NOT IN ('footway', 'cycleway', 'living_street', 'path', 'pedestrian', 'unclassified', 'unknown', 'service', 'steps')"
    arcpy.SelectLayerByAttribute_management('temp', 'NEW_SELECTION', expression)
    arcpy.CopyFeatures_management('temp', city_osm_road_select)
    arcpy.Delete_management('temp')

    arcpy.MakeFeatureLayer_management(city_osm_road_select, 'temp')
    arcpy.CopyFeatures_management('temp', city_osm_road)
    arcpy.Delete_management('temp')


def highwaysimp(city):
    """
    :param city: 待处理城市的名称（汉语拼音全拼 小写字母）
    :return: 返回当前城市简化后的高速路网（city + '_highway'）
    """
    # remove '%link%' class
    print city + ' Highway' + ' remove link roads...'
    fclass_remove = ['trunk_link', 'motorway_link']
    arcpy.MakeFeatureLayer_management(city + '_highway', "lyr")  # read in original highway data
    arcpy.SelectLayerByAttribute_management("lyr", "NEW_SELECTION",
                                            '"fclass" NOT IN (\'' + '\',\''.join(map(str, fclass_remove)) + '\')')
    arcpy.CopyFeatures_management("lyr", city + "_hnl")
    arcpy.Delete_management("lyr")

    # Project to Asia Lambert
    out_coordinate_system = arcpy.SpatialReference(102012)
    arcpy.Project_management(city + "_hnl", city + "_hnlproj", out_coordinate_system)

    arcpy.MakeFeatureLayer_management(city + "_hnlproj", 'lyr')
    arcpy.CopyFeatures_management('lyr', city + '_hnl')
    arcpy.Delete_management('lyr')

    # add merge field = 1
    print city + ' Highway' + ' adding field and calculating...'
    arcpy.MultipartToSinglepart_management(city + '_hnl', city + '_hnl_sin')
    arcpy.AddField_management(city + '_hnl_sin', "merge", "SHORT")
    arcpy.CalculateField_management(city + '_hnl_sin', "merge", 1, "PYTHON_9.3")

    # merge divided roads
    print city + ' Highway' + ' merging divided roads...'
    arcpy.MergeDividedRoads_cartography(city + '_hnl_sin', "merge", "20 Meters",
                                        city + '_hnl_sin_mer20', "")
    arcpy.MergeDividedRoads_cartography(city + '_hnl_sin_mer20', "merge", "20 Meters",
                                        city + '_hnl_sin_mer20_20', "")
    arcpy.MergeDividedRoads_cartography(city + '_hnl_sin_mer20_20', "merge", "20 Meters",
                                        city + '_hnl_sin_mer20_20_20', "")
    arcpy.MultipartToSinglepart_management(city + '_hnl_sin_mer20_20_20', city + '_hnl_sin_mer20_20_20_sin')
    arcpy.MergeDividedRoads_cartography(city + '_hnl_sin_mer20_20_20_sin', "merge", "50 Meters",
                                        city + '_hnl_sin_mer20_20_20_sin_50', "")
    arcpy.MergeDividedRoads_cartography(city + '_hnl_sin_mer20_20_20_sin_50', "merge", "50 Meters",
                                        city + '_hnl_sin_mer20_20_20_sin_50_50', "")
    arcpy.MergeDividedRoads_cartography(city + '_hnl_sin_mer20_20_20_sin_50_50', "merge", "50 Meters",
                                        city + '_hnl_sin_mer20_20_20_sin_50_50_50', "")
    arcpy.MultipartToSinglepart_management(city + '_hnl_sin_mer20_20_20_sin_50_50_50',
                                           city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin')
    arcpy.MergeDividedRoads_cartography(city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin', "merge", "100 Meters",
                                        city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100', "")
    arcpy.MergeDividedRoads_cartography(city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100', "merge", "100 Meters",
                                        city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100_100', "")
    arcpy.MergeDividedRoads_cartography(city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100_100', "merge", "100 Meters",
                                        city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100_100_100', "")
    arcpy.MultipartToSinglepart_management(city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100_100_100',
                                           city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100_100_100_sin')
    arcpy.MergeDividedRoads_cartography(city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100_100_100_sin', "merge",
                                        "150 Meters",
                                        city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100_100_100_sin_150', "")
    arcpy.MergeDividedRoads_cartography(city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100_100_100_sin_150', "merge",
                                        "150 Meters",
                                        city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100_100_100_sin_150_150', "")
    arcpy.MergeDividedRoads_cartography(city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100_100_100_sin_150_150', "merge",
                                        "150 Meters",
                                        city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100_100_100_sin_150_150_150', "")

    # optimize highway
    print city + " Highway" + " optimize..."
    arcpy.CopyFeatures_management(city + '_hnl_sin_mer20_20_20_sin_50_50_50_sin_100_100_100_sin_150_150_150',
                                  city + "_hnl_sin_merge_int")
    arcpy.Integrate_management(city + "_hnl_sin_merge_int", "50 Meters")

    arcpy.CopyFeatures_management(city + "_hnl_sin_merge_int", city + "_hnl_sin_merge_int_deleteid")
    arcpy.DeleteIdentical_management(city + "_hnl_sin_merge_int_deleteid", "shape")

    # Project to WGS84
    out_coordinate_system = arcpy.SpatialReference(4326)
    arcpy.Project_management(city + "_hnl_sin_merge_int_deleteid", city + "_hnlsimpproj", out_coordinate_system)
    # save the final result of highway to a simple name and convenient path
    arcpy.MakeFeatureLayer_management(city + "_hnlsimpproj", 'lyr')
    arcpy.CopyFeatures_management('lyr', city + '_highway')
    arcpy.Delete_management('lyr')

    print city + ' Highway' + ' Finished!'


def unhighwaysimp(city):
    """
    :param city: 待处理城市的名称（汉语拼音全拼 小写字母）
    :return: 返回当前城市简化后的非高速路网（city + '_unhighway'）
    """
    # remove some attributes (the known unimportant roads; and 'link' roads)
    print city + ' unHighway' + ' removing link roads...'
    fclass_remove = ['footway', 'cycleway', 'living_street', 'path', 'pedestrian', 'unclassified', 'unknown', 'service',
                     'steps', 'primary_link', 'secondary_link', 'tertiary_link']
    arcpy.MakeFeatureLayer_management(city + "_road", "lyr")  # read in original unhighway data
    arcpy.SelectLayerByAttribute_management("lyr", "NEW_SELECTION",
                                            '"fclass" NOT IN (\'' + '\',\''.join(map(str, fclass_remove)) + '\')')
    arcpy.CopyFeatures_management("lyr", city + "_uhs")
    arcpy.Delete_management('lyr')

    # Project to Asia Lambert
    out_coordinate_system = arcpy.SpatialReference(102012)
    arcpy.Project_management(city + "_uhs", city + "_uhsproj", out_coordinate_system)

    arcpy.MakeFeatureLayer_management(city + "_uhsproj", 'lyr')
    arcpy.CopyFeatures_management('lyr', city + '_uhs')
    arcpy.Delete_management('lyr')

    # export residential way, multitosingle and merge divided roads
    print city + ' unHighway' + ' dealing with residential roads...'
    arcpy.MakeFeatureLayer_management(city + "_uhs", 'temp_lyr')
    arcpy.SelectLayerByAttribute_management('temp_lyr', "NEW_SELECTION", "\"fclass\" = 'residential'")
    arcpy.CopyFeatures_management('temp_lyr', city + '_res')
    arcpy.Delete_management('temp_lyr')

    arcpy.MultipartToSinglepart_management(city + '_res', city + "_res_sin")
    arcpy.AddField_management(city + '_res_sin', "merge", "SHORT")
    arcpy.CalculateField_management(city + '_res_sin', "merge", 1, "PYTHON_9.3")
    arcpy.MergeDividedRoads_cartography(city + '_res_sin', "merge", "20 Meters",
                                        city + '_res_sin_mer20', "")
    arcpy.MergeDividedRoads_cartography(city + '_res_sin_mer20', "merge", "40 Meters",
                                        city + '_res_sin_mer20_40', "")
    arcpy.MergeDividedRoads_cartography(city + '_res_sin_mer20_40', "merge", "50 Meters",
                                        city + '_res_sin_mer20_40_50', "")
    arcpy.MergeDividedRoads_cartography(city + '_res_sin_mer20_40_50', "merge", "50 Meters",
                                        city + '_res_sin_mer20_40_50_50', "")
    # save the final result of residential roads to a simple name and convenient path
    arcpy.MakeFeatureLayer_management(city + '_res_sin_mer20_40_50_50', 'lyr')
    arcpy.CopyFeatures_management('lyr', city + '_res_simp')
    arcpy.Delete_management('lyr')

    # export primary way, multitosingle and merge for several times
    print city + ' unHighway' + ' dealing with primary roads...'
    arcpy.MakeFeatureLayer_management(city + "_uhs", 'temp_lyr')
    arcpy.SelectLayerByAttribute_management('temp_lyr', "NEW_SELECTION", "\"fclass\" = 'primary'")
    arcpy.CopyFeatures_management('temp_lyr', city + '_pr')
    arcpy.Delete_management('temp_lyr')

    arcpy.MultipartToSinglepart_management(city + '_pr', city + '_pr_sin')
    arcpy.AddField_management(city + '_pr_sin', "merge", "SHORT")
    arcpy.CalculateField_management(city + '_pr_sin', "merge", 1, "PYTHON_9.3")
    arcpy.MergeDividedRoads_cartography(city + '_pr_sin', "merge", "50 Meters",
                                        city + '_pr_sin_mer50', "")  # 1st multitosingle and merge
    arcpy.MergeDividedRoads_cartography(city + '_pr_sin_mer50', "merge", "100 Meters",
                                        city + '_pr_sin_mer50_100', "")  # 2nd multitosingle and merge
    arcpy.MergeDividedRoads_cartography(city + '_pr_sin_mer50_100', "merge", "150 Meters",
                                        city + '_pr_sin_mer50_100_150', "")  # 3rd multitosingle and merge
    arcpy.MergeDividedRoads_cartography(city + '_pr_sin_mer50_100_150', "merge", "200 Meters",
                                        city + '_pr_sin_mer50_100_150_200', "")  # 4th multitosingle and merge
    # save the final result of primary roads to a simple name and convenient path
    arcpy.MakeFeatureLayer_management(city + '_pr_sin_mer50_100_150_200', 'lyr')
    arcpy.CopyFeatures_management('lyr', city + '_pr_simp')
    arcpy.Delete_management('lyr')

    # export secondary way, multitosingle and merge for several times
    print city + ' unHighway' + ' dealing with secondary roads...'
    arcpy.MakeFeatureLayer_management(city + "_uhs", 'temp_lyr')
    arcpy.SelectLayerByAttribute_management('temp_lyr', "NEW_SELECTION", "\"fclass\" = 'secondary'")
    arcpy.CopyFeatures_management('temp_lyr', city + '_sec')
    arcpy.Delete_management('temp_lyr')

    arcpy.MultipartToSinglepart_management(city + '_sec', city + '_sec_sin')
    arcpy.AddField_management(city + '_sec_sin', "merge", "SHORT")
    arcpy.CalculateField_management(city + '_sec_sin', "merge", 1, "PYTHON_9.3")
    arcpy.MergeDividedRoads_cartography(city + '_sec_sin', "merge", "25 Meters",
                                        city + '_sec_sin_mer25', "")  # 1st multitosingle and merge
    arcpy.MergeDividedRoads_cartography(city + '_sec_sin_mer25', "merge", "50 Meters",
                                        city + '_sec_sin_mer25_50', "")  # 2nd multitosingle and merge
    arcpy.MergeDividedRoads_cartography(city + '_sec_sin_mer25_50', "merge", "100 Meters",
                                        city + '_sec_sin_mer25_50_100', "")  # 3rd multitosingle and merge
    arcpy.MergeDividedRoads_cartography(city + '_sec_sin_mer25_50_100', "merge", "150 Meters",
                                        city + '_sec_sin_mer25_50_100_150', "")  # 4th multitosingle and merge
    # save the final result of secondary roads to a simple name and convenient path
    arcpy.MakeFeatureLayer_management(city + '_sec_sin_mer25_50_100_150', 'lyr')
    arcpy.CopyFeatures_management('lyr', city + '_sec_simp')
    arcpy.Delete_management('lyr')

    # export tertiary way, multitosingle and merge for several times
    print city + ' unHighway' + ' dealing with tertiary roads...'
    arcpy.MakeFeatureLayer_management(city + "_uhs", 'temp_lyr')
    arcpy.SelectLayerByAttribute_management('temp_lyr', "NEW_SELECTION", "\"fclass\" = 'tertiary'")
    arcpy.CopyFeatures_management('temp_lyr', city + '_ter')
    arcpy.Delete_management('temp_lyr')

    arcpy.MultipartToSinglepart_management(city + '_ter', city + '_ter_sin')
    arcpy.AddField_management(city + '_ter_sin', "merge", "SHORT")
    arcpy.CalculateField_management(city + '_ter_sin', "merge", 1, "PYTHON_9.3")
    arcpy.MergeDividedRoads_cartography(city + '_ter_sin', "merge", "50 Meters",
                                        city + '_ter_sin_mer50', "")  # 1st  merge
    arcpy.MergeDividedRoads_cartography(city + '_ter_sin_mer50', "merge", "100 Meters",
                                        city + '_ter_sin_mer50_100', "")  # 2nd  merge
    arcpy.MergeDividedRoads_cartography(city + '_ter_sin_mer50_100', "merge", "150 Meters",
                                        city + '_ter_sin_mer50_100_150', "")  # 3rd  merge
    arcpy.MergeDividedRoads_cartography(city + '_ter_sin_mer50_100_150', "merge", "150 Meters",
                                        city + '_ter_sin_mer50_100_150_150', "")  # 4th  merge
    arcpy.MergeDividedRoads_cartography(city + '_ter_sin_mer50_100_150_150', "merge", "150 Meters",
                                        city + '_ter_sin_mer50_100_150_150_150', "")  # 5th  merge
    # save the final result of tertiary roads to a simple name and convenient path
    arcpy.MakeFeatureLayer_management(city + '_ter_sin_mer50_100_150_150_150', 'lyr')
    arcpy.CopyFeatures_management('lyr', city + '_ter_simp')
    arcpy.Delete_management('lyr')

    # export other way, no need to simplify
    print city + ' unHighway' + ' dealing with other roads...'
    roadtypes = ['primary', 'secondary', 'tertiary', 'residential']
    arcpy.MakeFeatureLayer_management(city + "_uhs", "lyr")
    arcpy.SelectLayerByAttribute_management("lyr", "NEW_SELECTION",
                                            '"fclass" NOT IN (\'' + '\',\''.join(map(str, roadtypes)) + '\')')
    arcpy.CopyFeatures_management("lyr", city + "_other")
    arcpy.Delete_management('lyr')

    arcpy.MultipartToSinglepart_management(city + '_other', city + '_other_sin')
    arcpy.AddField_management(city + '_other_sin', "merge", "SHORT")
    arcpy.CalculateField_management(city + '_other_sin', "merge", 1, "PYTHON_9.3")
    arcpy.MergeDividedRoads_cartography(city + '_other_sin', "merge", "50 Meters",
                                        city + '_other_sin_mer50', "")  # 1st  merge
    # save the final result of tertiary roads to a simple name and convenient path
    arcpy.MakeFeatureLayer_management(city + '_other_sin_mer50', 'lyr')
    arcpy.CopyFeatures_management('lyr', city + '_other_simp')
    arcpy.Delete_management('lyr')

    # Merge all kind of unhighway roads together (primary, secondary, tertiary, residential and other)
    # and multi to single and merge divided roads
    print city + ' unHighway' + ' dealing with merged roads...'
    arcpy.Merge_management([city + '_pr_simp',
                            city + '_sec_simp',
                            city + '_ter_simp',
                            city + '_res_simp',
                            city + '_other_simp'], city + '_uhs_simp')

    arcpy.MultipartToSinglepart_management(city + "_uhs_simp", city + "_uhs_simp_sin")
    arcpy.MergeDividedRoads_cartography(city + "_uhs_simp_sin", "merge", "50 Meters",
                                        city + "_uhs_simp_sin_mer50", "")
    arcpy.MergeDividedRoads_cartography(city + "_uhs_simp_sin_mer50", "merge", "50 Meters",
                                        city + "_uhs_simp_sin_mer50_50", "")

    # Project to WGS84
    out_coordinate_system = arcpy.SpatialReference(4326)
    arcpy.Project_management(city + "_uhs_simp_sin_mer50_50", city + "_uhssimpproj", out_coordinate_system)
    # save the final result of simplified roads to a simple name and convenient path
    arcpy.MakeFeatureLayer_management(city + "_uhssimpproj", 'lyr')
    arcpy.CopyFeatures_management('lyr', city + '_road')
    arcpy.Delete_management('lyr')

    print city + ' unHighway' + ' Finished!!!'


def seperate_highway_road(city):
    """
    :param city: 待处理城市名称
    :return: 该城市的siwei路网高速和非高速分类，输出city_swhighway,city_swroad
    """
    print city + ' seperate highway/road...'
    city_siwei = siweidir + "\\" + city
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


# ======================================================================================================================
'''
函数定义部分结束，以下为循环运行部分
'''

# create keeplist for keeping the result files
keeplist = []

for city in citylist:
    print(city)
    # ---从全国osm路网中裁剪出各个城市范围的osm路网
    clip_city_original_osm(city)

    # ---当name字段为空而ref字段有信息时，将ref信息补充到name
    name_ref(city)

    # ---将每个城市的osm路网高速和非高速部分分离开
    seperate_highway_unhighway(city)

    # ---将每个城市中非高速中需要简化的路段提取出来
    unhighway_select(city)

    # ---简化高速路网
    highwaysimp(city)

    # ---简化非高速路网
    unhighwaysimp(city)

    # ---添加需要保留的文件
    keeplist.append(city + '_highway')
    keeplist.append(city + '_road')
    keeplist.append(city + '_swhighway')
    keeplist.append(city + '_swroad')
print 'All cities finished!!!'

# 删除中间文件
print 'Deleting unused files...'
files = arcpy.ListFeatureClasses()
for fl in files:
    if fl not in keeplist:
        arcpy.Delete_management(fl)
print "delete files Finished!"

# seperate siwei data to _swhighway and _swroad & add siwei roads to osm roads
for city in citylist:
    # ---提取siwei路段的高速和非高速部分
    seperate_highway_road(city)

    # ---合并siwei和osm的高速路段
    addonroads(city + "_highway", city + "_swhighway")

    # ---合并siwei和osm的非高速路段
    addonroads(city + "_road", city + "_swroad")
    print city + ' finished!!!'

# deal with attribute table
for city in citylist:
    # ---将合并后name字段缺失的部分用pathname字段补充
    name_pathname(city)

    # ---将合并后fclass字段缺失的部分用rdClass字段补充
    fclass_rdclass(city)

    # ---将name字段None值缺失的部分用‘ ’补充
    name_str(city)

    # ---将fclass字段None值缺失的部分用‘ ’补充
    fclass_str(city)

    # ---删除多余的字段仅保留属性表前六列
    del_field(city)
    print city + ' process attribute table finished!!!'

keeplist = []
# complete keeplist and delete unused files
for city in citylist:
    keeplist.append(city + "_highway")
    keeplist.append(city + "_swhighway")
    keeplist.append(city + "_road")
    keeplist.append(city + "_swroad")
    keeplist.append(city + "_highway" + "_osm_add_siwei")
    keeplist.append(city + "_road" + "_osm_add_siwei")
    keeplist.append(city + "_highway_addon")
    keeplist.append(city + "_road_addon")

files = arcpy.ListFeatureClasses()
for fl in files:
    if fl not in keeplist:
        arcpy.Delete_management(fl)
print "Finish delete files!!!"
