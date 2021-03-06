"""
AUTOMATION: FLAGGING ERRORS

Sources:
    Michael Minn DeleteDuplicateGeometries.py
    https://bit.ly/2MfHmSG
    Peter Smythe Disconnected Islands plugin
    Ben W, GIS stack exchange 
    
To Do: 
    Gaps/dangles: still need to identify more traditional gaps and dangles (missing a lot)
    Islands: check discrepancy with ArcMap Geometry Checker (see txt files for affected fids)

Less important:
    Error_fields: change so no values added/changed if error field already exists 
    Try to use global variables for syntax cleanliness 
    load_layer: figure out user input and changing files 
    Potentially split finding and flagging errors into different functions for easier fixing later
"""

import qgis.utils
import qgis.analysis
import networkx as nx
import time
import os

def load_layer():

    file = "C:/Users/julia/Documents/vancouver/automation/merged_org.shp"
    layer = iface.addVectorLayer(file, "Merged", 'ogr')
    
    if not layer:
        print("layer not loaded")
    
    print("load_layer done")


def error_field():

    layer = iface.activeLayer()
    layer.startEditing()

    new_field = 'error'
    layer.addAttribute(QgsField(new_field, QVariant.Int))
    layer.updateFields()

    all_feat = layer.getFeatures()
    error_idx = layer.fields().lookupField('error')

    for feature in all_feat:
        layer.changeAttributeValue(feature.id(), error_idx, 0)

    print("error_field done")


def no_length():

    layer = iface.activeLayer()
    expr = QgsExpression("length = 0")
    selection = layer.getFeatures(QgsFeatureRequest(expr))
    error_idx = layer.fields().lookupField('error')

    for feature in selection:
        layer.changeAttributeValue(feature.id(), error_idx, 1)
        
    print("no_length done")


def invalid_geom():
    
    layer = iface.activeLayer()
    features = layer.getFeatures()
    index = QgsSpatialIndex()
    geoms = dict()
    invalid_ft = dict(geoms)
    
    for current, f in enumerate(features):
        if not f.hasGeometry():
            null_features.add(f.id())
            continue

        geoms[f.id()] = f.geometry()
        index.addFeature(f)

    for feature_id, geometry in geoms.items():
        if feature_id not in invalid_ft:
            continue

        for feature_id in invalid_ft:
            if geometry.isGeosValid(geoms[candidate_id]):
                invalid_ft.remove(feature_id)

    error_idx = layer.fields().lookupField('error')
    for feature_id in invalid_ft:
        fid = feature_id
        layer.changeAttributeValue(fid, error_idx, 1)

    print("invalid_geom done")


def duplicates():

    layer = iface.activeLayer()
    features = layer.getFeatures()
    index = QgsSpatialIndex()
    
    geoms = dict()
    dup_features = list()
    null_features = set()

    for current, f in enumerate(features):
        if not f.hasGeometry():
            null_features.add(f.id())
            continue

        geoms[f.id()] = f.geometry()
        index.addFeature(f)

    unique_features = dict(geoms)

    for feature_id, geometry in geoms.items():
        if feature_id not in unique_features:
            continue

        candidates = index.intersects(geometry.boundingBox())
        candidates.remove(feature_id)

        for candidate_id in candidates:
            if geometry.isGeosEqual(geoms[candidate_id]):
                dup_features.append(feature_id)

    error_idx = layer.fields().lookupField('error')
    for feature_id in dup_features:
        fid = feature_id
        layer.changeAttributeValue(fid, error_idx, 1)

    print("duplicates done")


def islands():

    layer = iface.activeLayer()
    G = nx.Graph() #nondirectional graph

    for feat in layer.getFeatures():
        geom = feat.geometry()
        QgsGeometry.convertToSingleType(geom)
        line = geom.asPolyline()
        for i in range(len(line)-1):
            G.add_edges_from([((line[i][0], line[i][1]), (line[i+1][0], line[i+1][1]),
                              {'fid': feat.id()})])

    connected_components = list(nx.connected_component_subgraphs(G))

    fid_comp = {}
    for i, graph in enumerate(connected_components):
       for edge in graph.edges(data=True):
           fid_comp[edge[2].get('fid', None)] = i

    countMap = {}
    for v in fid_comp.values():
        countMap[v] = countMap.get(v,0) + 1
    isolated = [k for k, v in fid_comp.items() if countMap[v] == 1]

    error_idx = layer.fields().lookupField('error')
    for feature in isolated:
        layer.changeAttributeValue(feature, error_idx, 1)

    print("islands done")


def pairs():

    #Dangles section: 1 neighbor connected, segment <2m long
    #This section flaggs subnetworks with only two components - finds flags, dangles, connected islands
      
    layer = iface.activeLayer()
    G = nx.Graph() 

    for feat in layer.getFeatures():
        geom = feat.geometry()
        QgsGeometry.convertToSingleType(geom)
        line = geom.asPolyline()
        for i in range(len(line)-1):
            G.add_edges_from([((line[i][0], line [i][1]), (line[i+1][0], line[i+1][1]),
                               {'fid': feat.id()})])

    connected_components = list(nx.connected_component_subgraphs(G))

    fid_comp = {}
    for i, graph in enumerate(connected_components):
        for edge in graph.edges(data=True):
            fid_comp[edge[2].get('fid', None)] = i
    
    countMap = {}
    for v in fid_comp.values():
        countMap[v] = countMap.get(v,0) + 1
    singleConn = [k for k, v in fid_comp.items() if countMap[v] == 2]
    
    error_idx = layer.fields().lookupField('error')
    for feature in singleConn:
        layer.changeAttributeValue(feature, error_idx, 1)

    print("pairs (some dangles, some gaps) done")


def fragments():

    layer = iface.activeLayer()
    selection = layer.selectByExpression("length < 2")

    fragments = layer.selectedFeatureCount()
    allSeg = layer.featureCount()
    pct = round(fragments/allSeg*100, 2)
    
    print(f"Fragments: {fragments}\nPct of total: {pct}%")
    
    layer.removeSelection()

# Prepping file for flagging
load_layer()
error_field()
#os.system('pause') 

start = time.time()

# Flagging errors
invalid_geom()
no_length()
duplicates()
islands()
pairs()
fragments()

end = time.time()
runtime = int(end - start)

layer = iface.activeLayer()
layer.selectByExpression("error = 1")
errors = layer.selectedFeatureCount()
pctErrors = int(errors/2368*100)

print(f"""Script completed. 
Errors flagged: {errors}
Compared to manual: {pctErrors}%
Runtime: {runtime}""")

layer.removeSelection()