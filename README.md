# blender-pathgraph

### Add-on for Blender
![Screenshot of blender-pathgraph](http://only-dev.kz/pathgraph.png)
Adds a menu while editing a mesh, where you can set the name(place) for vertexes and export as a graph
```js
// Exported json
  {
    "verts": [
      {
        "coords": [0, 0, 0],
        "place": ""
      }
      // ...
    ],
    "graph": NetworkX Graph().to_dict_of_dicts()
  }
```
