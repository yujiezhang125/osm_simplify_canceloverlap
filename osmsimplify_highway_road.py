# -*- coding: utf-8 -*-
# @Time    : 2020/03/17
# @Author  : XiaoShan
# @FileName: osmsimplify_highway_road.py
# @Description: Seperate osm highway and non-highway into two part.
# @Description: Simplify highway and non-highway, and merge multi-line roads to single-line roads

import arcpy
import pandas as pd

arcpy.env.workspace = r'D:\CityDNA\Data\Simplification\codetest.gdb'
arcpy.env.overwriteOutput = True

# 需重新定义china_osm2020, clip_root, workdir三个路径！
# read in osm data of whole country
china_osm2020 = r'D:\cityDNA\Data\Simplification\gis_osm_roads_free_1\gis_osm_roads_free_1.shp'
# read in 38 cities' boundary
clip_root = r'D:\cityDNA\Data\Simplification\china_city_osm'
# output path
workdir = arcpy.env.workspace + '\\'


def clip_city_original_osm(city):
    """
    :param city: 待处理城市的名称（汉语拼音全拼 小写字母）
    :return: 返回当前城市的osm路网
    """
    print city + ' clipping...'
    boundary = clip_root + '\\boundary_38\\' + city + '.shp'
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
    city_osm_highway = workdir + city + 'highway'
    city_osm_unhighway = workdir + city + 'unhighway'
    arcpy.MakeFeatureLayer_management(city_osm, 'city_osm')
    arcpy.SelectLayerByAttribute_management('city_osm', 'NEW_SELECTION',
                                            "fclass LIKE 'motorway%' OR fclass LIKE 'trunk%'")
    arcpy.CopyFeatures_management('city_osm', city_osm_highway)
    arcpy.SelectLayerByAttribute_management('city_osm', 'SWITCH_SELECTION',
                                            "fclass LIKE 'motorway%' OR fclass LIKE 'trunk%'")
    arcpy.CopyFeatures_management('city_osm', city_osm_unhighway)
    arcpy.Delete_management('city_osm')


def unhighway_select(city):
    """
    :param city: 待处理城市的名称（汉语拼音全拼 小写字母）
    :return: 分别返回当前城市非高速路网筛选后的结果（city + 'unhighway_selected'）
    """
    print city + ' unhighway select...'
    city_osm_unhighway = workdir + city + 'unhighway'
    city_osm_unhighway_select = workdir + city + 'unhighway_selected'
    arcpy.MakeFeatureLayer_management(city_osm_unhighway, 'temp')
    expression = "fclass NOT IN ('footway', 'cycleway', 'living_street', 'path', 'pedestrian', 'unclassified', 'unknown', 'service', 'steps')"
    arcpy.SelectLayerByAttribute_management('temp', 'NEW_SELECTION', expression)
    arcpy.CopyFeatures_management('temp', city_osm_unhighway_select)
    arcpy.Delete_management('temp')


def highwaysimp(city):
    """
    :param city: 待处理城市的名称（汉语拼音全拼 小写字母）
    :return: 返回当前城市简化后的高速路网（city + '_highway'）
    """
    # remove '%link%' class
    print city + ' Highway' + ' remove link roads...'
    fclass_remove = ['trunk_link', 'motorway_link']
    arcpy.MakeFeatureLayer_management(city + 'highway', "lyr")  # read in original highway data
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
    arcpy.MakeFeatureLayer_management(city + "unhighway", "lyr")  # read in original unhighway data
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


# ======================================================================================================================
'''
函数定义部分结束，以下为循环运行部分
'''

# read in citylist
citylist = pd.read_csv(clip_root + '\\city.csv', engine='python')['Name_EN'].tolist()

arcpy.env.workspace = r'D:\CityDNA\Data\Simplification\codetest.gdb'
arcpy.env.overwriteOutput = True

# create keeplist for keeping the result files
keeplist = []

for city in citylist:
    print(city)
    # ---从全国osm路网中裁剪出各个城市范围的osm路网
    clip_city_original_osm(city)

    # ---当name字段为空而ref字段有信息时，将ref信息补充到name
    name_ref(city)

    # ---将每个城市的高速和非高速部分分离开
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
print 'All cities finished!!!'

# 删除中间文件
print 'Deleting unused files...'
files = arcpy.ListFeatureClasses()
for fl in files:
    if fl not in keeplist:
        arcpy.Delete_management(fl)
print city + " Finished!"
