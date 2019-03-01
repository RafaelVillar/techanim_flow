# techanim_flow
Tools for creating and managing a Techanim workflow geared towards Maya and nCloth, specifically.
With something as complex as nCloth simulation in maya, there are many approaches that can be taken. Instead of trying to impose a single approach
onto everyone, I thought a set of tools that simply organizes the geometry and quickly gets out of your way would be best.
With simming, you need to prepare the geometry, simulate it, and then clean it up. So the idea of these tools is to break up the desired geo
into 3 layers. Pre, Sim, and Post. Each layer connected to the next. 

The entire TechAnim toolset is configurable, an example config below.
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
 
}
