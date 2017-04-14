# !/usr/bin/env python
"""Assess Getty Authorities Data."""
import rdflib
from SPARQLWrapper import SPARQLWrapper, JSON
import time
import pprint

# Global Namespaces
GVP = rdflib.Namespace("http://vocab.getty.edu/ontology#")
Schema = rdflib.Namespace("http://schema.org/")
wgs = rdflib.Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")
gettysparql = SPARQLWrapper("http://vocab.getty.edu/sparql")


class RepoInvestigatorException(Exception):
    """This is our base exception for this script."""

    def __init__(self, value):
        """Exception Object init."""
        self.value = value

    def __str__(self):
        """String value of exception."""
        return "%s" % (self.value,)


def collect_stats(stats_agg, stats):
    """Collect field usage statistics.
    The following methods are all for taking a dictionary of field usage
    statistics and generate the overall assessment output.
    """
    # increment the record counter
    stats_agg["record_count"] += 1

    for field in stats:
        # get the total number of times a field occurs
        stats_agg["field_info"].setdefault(field, {"field_count": 0})
        stats_agg["field_info"][field]["field_count"] += 1

        # get average of all fields
        stats_agg["field_info"][field].setdefault("field_count_total", 0)
        stats_agg["field_info"][field]["field_count_total"] += stats[field]


def create_stats_averages(stats_agg):
    """Generate field averages for field usage statistics output."""
    for field in stats_agg["field_info"]:
        field_count = stats_agg["field_info"][field]["field_count"]
        field_count_total = stats_agg["field_info"][field]["field_count_total"]

        field_count_total_average = (float(field_count_total) /
                                     float(stats_agg["record_count"]))
        stats_agg["field_info"][field]["field_count_total_average"] = field_count_total_average

        field_count_element_average = (float(field_count_total) / float(field_count))
        stats_agg["field_info"][field]["field_count_element_average"] = field_count_element_average

    return stats_agg


def pretty_print_stats(stats_averages):
    """Print the field usage statistics and averages."""
    record_count = stats_averages["record_count"]
    # get header length
    element_length = 0
    for element in stats_averages["field_info"]:
        if element_length < len(element):
            element_length = len(element)

    print("\n\n")
    for element in sorted(stats_averages["field_info"]):
        percent = (stats_averages["field_info"][element]["field_count"] /
                   float(record_count)) * 100
        percentPrint = "=" * (int((percent) / 4))
        columnOne = " " * (element_length - len(element)) + element
        print("%s: |%-25s| %6s/%s | %3d%% " % (
                    columnOne,
                    percentPrint,
                    stats_averages["field_info"][element]["field_count"],
                    record_count,
                    percent
                ))


def main():
    """Main operation of script."""
    # start the field usage statistics dictionary that will be used later.
    stats_agg = {
        "record_count": 0,
        "field_info": {}
    }

    concepts = [GVP.AdminPlaceConcept, GVP.PersonConcept, GVP.GroupConcept, GVP.PhysPlaceConcept]
    RWOs = [Schema.Person, Schema.Organization, Schema.Place, wgs.SpatialThing]
    s = 0
    for concept in concepts:
        print("Concept: " + concept)
        # Get all instances of chosen Concept class
        gettysparql.setQuery("""
        PREFIX GVP: <http://vocab.getty.edu/ontology#>
        SELECT DISTINCT ?concept WHERE {
           ?concept rdf:type """ + concept.n3() + """ .
        }
        """)
        time.sleep(.25)
        gettysparql.setReturnFormat(JSON)
        results = gettysparql.query().convert()
        conceptInstances = []
        for result in results['results']['bindings']:
            conceptInstances.append(result['concept']['value'])

        for instance in conceptInstances:
            if (s % 500) == 0 and s != 0:
                print("%d instances processed" % s)
                stats_averages = create_stats_averages(stats_agg)
                pretty_print_stats(stats_averages)
            s += 1
            stats = {}

            # Get unique properties used for Concept instance
            gettysparql.setQuery("""
            PREFIX GVP: <http://vocab.getty.edu/ontology#>
            SELECT ?conceptPred (COUNT(?conceptPred) as ?predCount)
            WHERE {
               <""" + instance + """> ?conceptPred ?obj .
            }
            GROUP BY ?conceptPred
            """)
            time.sleep(1)
            gettysparql.setReturnFormat(JSON)
            results = gettysparql.query().convert()

            for result in results['results']['bindings']:
                pred = result['conceptPred']['value']
                predCount = result['predCount']['value']
                stats.setdefault(pred, 0)
                stats[pred] += int(predCount)
            collect_stats(stats_agg, stats)
        pprint.pprint(stats_agg)
        print('DONE with ' + concept)
        stats_averages = create_stats_averages(stats_agg)
        pretty_print_stats(stats_averages)

if __name__ == "__main__":
    main()
