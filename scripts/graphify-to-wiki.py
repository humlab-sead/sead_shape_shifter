import json
from pathlib import Path

from graphify.analyze import god_nodes
from graphify.cluster import score_all
from graphify.wiki import to_wiki
from networkx.readwrite import json_graph

data = json.loads(Path("graphify-out/graph.json").read_text())
G = json_graph.node_link_graph(data, edges="links")
communities = {}
for nid, d in G.nodes(data=True):
    cid = d.get("community")
    if cid is not None:
        communities.setdefault(int(cid), []).append(nid)
to_wiki(G, communities, "graphify-out/wiki", cohesion=score_all(G, communities), god_nodes_data=god_nodes(G))
