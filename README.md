#### <u>1.代码内容：（两套）</u>

osm_simplify_highway_road.py

osm_siwei_addonroads_canceloverlap.py

 

#### <u>2.作用：</u>

osm_siwei_simplify_highway_road.py：将每个城市的原始osm路网，分为高速部分和非高速部分；分别进行路网简化，尽量将多线并行状态的道路简化为单线道路。并将每个城市的siwei路网高速和非高速路段分别提取出来，并将四维路网中包含但是osm路网不包含的道路补充到osm路网中，形成每个城市完整版的高速和非高速路段。

osm_siwei_addonroads_canceloverlap.py：读入每个城市的完整版高速和非高速路段数据，删去和高速道路重合的非高速道路，并且将二者merge得到该城市的完整版全部路网数据。



#### <u>3.数据输入和输出：</u>

**osm_siwei_simplify_highway_road.py：**

需要输入或定义的变量:

Line11（arcpy.env.workspace）：工作环境，任意设在一个geodatabase中（.gdb）

Line15（china_osm2020）：需要读入的原始的全国osm数据的绝对路径

Line17（clip_root）：城市边界存储位置的绝对路径（该路径下应存储了用来裁剪全国osm数据的各个城市的边界文件，格式为.shp，城市边界的文件命名为该城市名汉语拼音的小写全拼，以哈尔滨为例，其城市边界文件名应为 haerbin.shp。如果城市边界文件存储在.gdb中，非.shp格式，则代码Line32末尾的 + ’.shp’请删去，命名规则同样为该城市名汉语拼音的小写全拼）

Line22（siweidir）：四维道路数据存储位置的绝对路径（该gdb路径下应为各个城市的四维道路数据，四维道路数据的文件命名为该城市名汉语拼音的小写全拼，以哈尔滨为例，其四维道路文件名应为 haerbin。如果城市边界文件存储在普通文件夹中，文件为.shp格式，则代码Line22末尾请添加上 + ’.shp’ ，命名规则同样为该城市名汉语拼音的小写全拼）

Line25（citylist）：读入待处理的城市名称，命名规则为该城市名汉语拼音的小写全拼。将城市名读取为一个list。如待处理城市为北京，乌鲁木齐，西安，哈尔滨4个城市，则读取后的citylist内容应该是[‘beijing’, ‘wulumuqi’, ‘xian’, ‘haerbin’]

\#####请运行全部代码=============================================================

输出数据：

将以上变量定义或读取完成后，运行全部代码，完成后请在Line11设置的gdb工作路径下查看结果。

结果数据为每个城市有8个文件 ：

| 文件名                     | 内容                                                |
| -------------------------- | --------------------------------------------------- |
| city_highway               | 简化后的该城市osm高速路段                           |
| city_road                  | 简化后的该城市osm非高速路段                         |
| city_swhighway             | 简化后的该城市四维高速路段                          |
| city_swroad                | 简化后的该城市四维非高速路段                        |
| city_highway_osm_add_siwei | 以osm路网为基底补上部分四维道路后的完整版高速路网   |
| city_road_osm_add_siwei    | 以osm路网为基底补上部分四维道路后的完整版非高速路网 |
| city_highway_addon         | 属性表处理之后的“city_highway_osm_add_siwei”数据    |
| city_road_addon            | 属性表处理之后的“city_road_osm_add_siwei”数据       |

（如果不想保留每个城市的8个文件，请在Line729 ~ Line736部分代码中删去不想保留的文件名即可）

 



**osm_siwei_addonroads_canceloverlap.py：**

需要输入或定义的变量:

Line11（arcpy.env.workspace）：工作环境，任意设在一个geodatabase中（.gdb）

Line15（simp_path）：简化合并后的数据存储的绝对路径。通常情况下simp_path应该和代码osm_siwei_simplify_highway_road.py中的’arcpy.env.workspace’相同

Line17（citylist）：读入待处理的城市名称，命名规则为该城市名汉语拼音的小写全拼。将城市名读取为一个list。如待处理城市为北京，乌鲁木齐，西安，哈尔滨4个城市，则读取后的citylist内容应该是[‘beijing’, ‘wulumuqi’, ‘xian’, ‘haerbin’] （大多数情况下此处的citylist和前一个代码中的citylist内容相同）

\#####请运行全部代码=============================================================

输出数据：

将以上变量定义或读取完成后，运行全部代码，完成后请在Line11设置的gdb工作路径下查看结果。

结果数据为每个城市有3个文件：

| 文件名                | 内容                                                         |
| --------------------- | ------------------------------------------------------------ |
| city_highway_addon    | 导入的完整版高速路段数据                                     |
| city_road_addon       | 导入的完整版非高速路段数据                                   |
| city_highway_add_road | 删去完整版非高速路网中与完整版高速路重合的路段后，将二者merge得到一个城市的全部简化版路网 |

（如果不想保留每个城市的3个文件，请在Line164 ~ Line166部分代码中删去不想保留的文件名即可）