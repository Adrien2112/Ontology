"""Espaces de noms partagés par l'outillage."""

from rdflib import Namespace
from rdflib.namespace import DCTERMS, OWL, PROV, RDF, RDFS, SH, SKOS, XSD

BASE = "https://adrien2112.github.io/ontology/"
DDD = Namespace(BASE + "ddd#")
REPO = Namespace(BASE + "repo#")
MEM = Namespace(BASE + "memory#")
MSH = Namespace(BASE + "meta-shapes#")
INV = Namespace(BASE + "invariants#")

__all__ = ["BASE", "DDD", "REPO", "MEM", "MSH", "INV", "DCTERMS", "OWL", "PROV", "RDF", "RDFS", "SH", "SKOS", "XSD"]


def bind_all(graph):
    for prefix, ns in {
        "ddd": DDD, "repo": REPO, "mem": MEM, "msh": MSH, "inv": INV,
        "dcterms": DCTERMS, "owl": OWL, "prov": PROV, "rdf": RDF, "rdfs": RDFS,
        "sh": SH, "skos": SKOS, "xsd": XSD,
    }.items():
        graph.bind(prefix, ns, override=True)
    return graph
