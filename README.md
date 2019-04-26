# techanim_flow
Tools for creating and managing a Techanim workflow geared towards Maya and nCloth, specifically.
With something as complex as nCloth simulation in maya, there are many approaches that can be taken. Instead of trying to impose a single approach
onto everyone, I thought a set of tools that simply organizes the geometry and quickly gets out of your way would be best.
With simming, you need to prepare the geometry, simulate it, and then clean it up. So the idea of these tools is to break up the desired geo
into 3 layers. Pre, Sim, and Post. Each layer connected to the next.

The entire TechAnim toolset is configurable, an example config below.

Any piece of geometry that will be simulated will be made into 3 layers for interaction. The visibility of all the layers is set to OFF, unless you are operating on that layer. This is to avoid confusion and retain acceptable playback.

シミュレーションされるジオメトリの任意の部分は、相互作用のために3つのレイヤーになります。そのレイヤーで操作していない限り、すべてのレイヤーの表示はOFFに設定されます。これは混乱を避け、許容できる再生を維持するためです。


Pre Layer: The layer prior to the simulation later. This is where you can create any necessary modifications to the geometry to prevent interpenetration, smooth wrinkles, etc.

Pre Layer（プレレイヤー）：シミュレーションの前のレイヤー。ここでは、めり込み、滑らかなしわなどを防ぐためにジオメトリに必要な変更を加えることができます。


Sim Layer: This is the layer with the active nCloth deformer. You use this layer to modify simulation settings such as stiffness, stretchiness.

Sim Layer：アクティブなnClothデフォーマを持つレイヤーです。このレイヤーを使用して、剛性、伸縮性などのシミュレーション設定を変更します。


Post Layer: This layer is for clean up after simulation. Smooth our a wrinkle or fix interpenetration caused during simulation.

ポストレイヤー：このレイヤーはシミュレーション後のクリーンアップ用です。シミュレーション中に起こるシワを和らげたり、めり込みを修正したりしてください。


TechAnim - UI will manage the creation, connection and cache management for the scene. The TechAnim setup will be local to the scene, not referenced.

TechAnim  -  UIはシーンの作成、接続、およびキャッシュ管理を管理します。 TechAnimの設定はシーンにローカルであり、Referenceではありません。

Technical - Back-end - TD
The only modification to the source rig/animation is rerouting the ".Output Geometry" connection from the latest deformer from the rig into the TechAnim setup. And then connect the ".outMesh" from the TechAnim into the ".inMesh" of the render geometry.

ソースリグ/アニメーションの唯一の変更は、 ".Output Geometry"接続をリグの最新デフォーマからTechAnimセットアップに再コネクトすることです。 TechAnimの ".outMesh"をレンダージオメトリの ".inMesh"に接続します。

Phases of implementation.
Phase 1

TechAnim Setup Creator: A set of tool(s) to create a setup used for simulation. This creates the layers.
TechAnim Setup Creator：クロースシミュレーションをセットアップ作成ツールでPre Layer、Sim Layer、Post Layerが作成されます。
TechAnim Sim Manager: The tool depicted above. The artist will interact with the simulation and caches via this UI.
TechAnim Sim Manager：上記のツールを利用してアーティストがシミュレーションとキャッシュを管理することが可能です。
Phase 2

Create a tool to auto t-pose animation, using animation layers.
アニメーションレイヤを使用して、自動T-Poseアニメーションを作成するツールを作成します。
Preset saving and sharing.
プリセット保存と共有。
Send simulations to the farm.
ファームにシミュレーションを送信します。
Phase 3

Create a tool to auto t-pose for alembic caches
alembicキャッシュの自動T-Poseツールを作成します。


```
{
    "#": "suffix for the nodes being created for the setup",
    "input_suffix": "_input",
    "output_suffix": "_output",
    "#": "group naming",
    "input_layer_name": "input",
    "output_layer_name": "output",
    "render_input": "render_input",
    "render_output": "render_output",
    "sim_input": "sim_input",
    "sim_output": "sim_output",
    "#": "Top node name",
    "techanim_root": "techanim_setup",
    "sim_base_name": "geo",
    "sim_layer": "sim",
    "post_layer": "post",
    "nCloth_suffix": "_nCloth",
    "nCloth_output_suffix": "_DISPLAY",
    "rigid_suffix": "_rigid",
    "nucleus_name": "techanim_nucleus",
    "config_attr": "techanim_config",
    "nodes_attr": "techanim_nodes",
    "preroll": 25,
    "postroll": 25,
    "nodes_to_hide": ["geo_pre", "geo_post", "geo_sim"],
    "suffixes_to_hide": ["_sim", "_DISPLAY"],
    "#": "The creator will make the grouping with the names and in the order",
    "#": "shown below.",
    "grouping": {
        "techanim_setup": {
            "pre": {
                "geo_pre": null
            },
            "input": {
                "render_input": null,
                "sim_input": null
            },
            "post": {
                "geo_post": null
            },
            "sim": {
                "geo_sim": null
            },
            "output": {
                "render_output": null,
                "sim_output": null
            }
        }
    },
    "grouping_order": ["input", "pre", "sim", "post", "output"],
    "cache_dir_suffix": "_techanim",
    "#": "if empty, it will use pythons tmpdir for cache_dir storing.",
    "cache_dir": "S:/ANIMA/projects/MST3/tmp/techanim",
    "HOWTO_FILEPATH_DICT": {
        "RenderGeoListView": "images/make_association.gif",
        "SimGeoListView": "images/make_association.gif",
        "AddRenderGeoButton": "images/add_render_geo.gif",
        "easter_egg": "images/muffin.gif"
    }

}```



## Usuage

## Techanim Creator

`from techanim_flow import techanim_creator_ui;
 techanim_creator_ui.show()`




## Techanim Manager

`from techanim_flow import techanim_manager_ui;
 techanim_manager_ui.show()`

## Preset Share

`from techanim_flow import preset_share_ui;
 preset_share_ui.show()`


## Changelog

***0.1.2***

    - Initial release.
    - toggle dynamic attr for nucleus and cloth shapes.

