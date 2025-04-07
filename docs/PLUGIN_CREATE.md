# Integration of a new plugin

##  Build the plugin
1. Create a new file in `analyser/inference_ray/src/plugins/`
2. Create a class inhereting from `AnalyserPlugin` with an `__init__` and a `call` method (signature and structure can be found in other plugins)
3. Register your class with a unique name using the decorator `@AnalyserPluginManager.export("your_plugin_name")`
4. Specify Input and Output data types in objects `requires` and `provides` (can be found in `analyser/data_python/src/plugins/`)
5. Import needed packages and load models inside the `call` method
6. If used models aren't downloaded automatically, place them in a subdirectory of `/data/models/` and access them with `/models/...`. (Models should be added to models cloud storage bucket later)
7. Add your new plugin to `analyser/inference_ray/deploy.yml` and to `analyser/inference_ray/deploy.cuda.yml` by adding:

    ```yml
    - name: your_plugin_name
    route_prefix: /your_plugin_name
    import_path: main:app_builder
    args:
        model: your_plugin_name
        data_path: /data
        params: {}
    deployments:
        - name: Deployment
        autoscaling_config:
            min_replicas: 0
        ray_actor_options:
            num_cpus: 2
            runtime_env:
            pip:
                - imported_dummy_package1==1.0.0
                - imported_dummy_package2==2.0.1

    ```
- Rerun (sudo) `docker-compose up --build` to include your new plugin
- Use logging.error("message") for debugging purposes inside your plugin
- Example of needed Stub for call method: 
    ```py
    with inputs as input_data, data_manager.create_data(
            "OutputDataType" # Has to be passed as a String e.g. "ListData"
        ) as output_data:
            # e.g. add AnnotationData entry to ListData object
            with output_data.create_data("AnnotationData") as ann_data:
                ann_data.annotations.extend(your_annotation) # e.g. data type Annotation
                ann_data.name = "name of data entry"

            self.update_callbacks(callbacks, progress=1.0)
            return {"annotations": output_data} # example of returning object with "annotations"
    ```

## Add plugin to backend
   1. Create a new file in `backend/backend/tasks/`
   2. Include the new file in `backend/backend/tasks/__init__.py`
   3. Create a class inhereting from `Parser` with an `__init__` method to parse plugin parameters and register it with: `@PluginManager.export_parser("your_plugin_name")`
   4. Create a class inhereting from `Task` with an `__init__` and a `__call__` method to include your plugin and register it with: ``@PluginManager.export_plugin("your_plugin_name")`
   5. Look at other plugins to get a notion of sophisticated class/method structures

## Make plugin accessable in frontend
   1. Add plugin to a group in `frontend/src/components/ModalPlugin.vue` with:
   ```js
   {
           name: t("modal.plugin.your_plugin_name.plugin_name"),
           description: t("modal.plugin.your_plugin_name.plugin_description"),
           icon: "your_plugin_icon", // from https://pictogrammers.com/library/mdi/
           plugin: "your_plugin_name",
           id: 101, // unique integers in ascending order (starting with group_id * 100 + 1: So for group 1 the first plugin has the id 101)
           parameters: [], // parameters to control adjustable plugin behaviour (lookup types in other plugins)
           optional_parameters: [], // parameters in an extendable window
   }
   ```
   2. Add plugin name, description... in `frontend/src/locales/en.json`:
   ```json
   "your_plugin_name": {
        "plugin_name": "Your Plugin Name",
        "plugin_description": "Your plugin description.",
        // ... add more custom variables if needed
   }
   ```
   3. Adjust name for run history in `frontend/src/components/History.vue` inside of pluginName(type) {...} by adding:
   ```js
   if (type === "your_plugin_name") {
        return t("modal.plugin.your_plugin_name.plugin_name");
      }
   ```