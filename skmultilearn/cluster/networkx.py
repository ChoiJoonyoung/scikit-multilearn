from __future__ import absolute_import

import community
import networkx as nx
import numpy as np
from builtins import range

from .base import LabelGraphClustererBase
from .helpers import _membership_to_list_of_communities


class NetworkXLabelGraphClusterer(LabelGraphClustererBase):
    """Cluster label space with NetworkX community detection

    This clusterer constructs a NetworkX representation of the Label Graph generated by graph builder and detects
    communities in it using methods from the NetworkX library. Detected communities are converted to
    a label space clustering.

    Parameters
    ----------
    graph_builder: a GraphBuilderBase inherited transformer
        the graph builder to provide the adjacency matrix and weight map for the underlying graph
    method: string
        the community detection method to use, this clusterer supports the following community detection methods:

        +----------------------+--------------------------------------------------------------------------------+
        | Method name string   |                             Description                                        |
        +----------------------+--------------------------------------------------------------------------------+
        | louvain_             | Detecting communities with largest modularity using incremental greedy search  |
        +----------------------+--------------------------------------------------------------------------------+
        | label_propagation_   | Detecting communities from multiple async label propagation on the graph       |
        +----------------------+--------------------------------------------------------------------------------+

        .. _louvain: https://python-louvain.readthedocs.io/en/latest/
        .. _label_propagation: https://networkx.github.io/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.label_propagation.asyn_lpa_communities.html


    Attributes
    ----------
    graph_ : networkx.Graph
        the networkx Graph object containing the graph representation of graph builder's adjacency matrix and weights_
    weights_ : { 'weight' : list of values in edge order of graph edges }
        edge weights_ stored in a format recognizable by the networkx module

    References
    ----------
    If you use this clusterer please cite the igraph paper and the clustering paper:

    .. code :: latex

        @unknown{networkx,
            author = {Hagberg, Aric and Swart, Pieter and S Chult, Daniel},
            year = {2008},
            month = {01},
            title = {Exploring Network Structure, Dynamics, and Function Using NetworkX},
            booktitle = {Proceedings of the 7th Python in Science Conference}
        }

        @article{blondel2008fast,
          title={Fast unfolding of communities in large networks},
          author={Blondel, Vincent D and Guillaume, Jean-Loup and Lambiotte, Renaud and Lefebvre, Etienne},
          journal={Journal of statistical mechanics: theory and experiment},
          volume={2008},
          number={10},
          pages={P10008},
          year={2008},
          publisher={IOP Publishing}
        }


    Examples
    --------

    An example code for using this clusterer with a classifier looks like this:

    .. code-block:: python

        from sklearn.ensemble import RandomForestClassifier
        from skmultilearn.problem_transform import LabelPowerset
        from skmultilearn.cluster import NetworkXLabelGraphClusterer, LabelCooccurrenceGraphBuilder
        from skmultilearn.ensemble import LabelSpacePartitioningClassifier

        # construct base forest classifier
        base_classifier = RandomForestClassifier(n_estimators=1000)

        # construct a graph builder that will include
        # label relations weighted by how many times they
        # co-occurred in the data, without self-edges
        graph_builder = LabelCooccurrenceGraphBuilder(
            weighted = True,
            include_self_edges = False
        )

        # setup problem transformation approach with sparse matrices for random forest
        problem_transform_classifier = LabelPowerset(classifier=base_classifier,
            require_dense=[False, False])

        # setup the clusterer to use, we selected the modularity-based approach
        clusterer = NetworkXLabelGraphClusterer(graph_builder=graph_builder, method='louvain')

        # setup the ensemble metaclassifier
        classifier = LabelSpacePartitioningClassifier(problem_transform_classifier, clusterer)

        # train
        classifier.fit(X_train, y_train)

        # predict
        predictions = classifier.predict(X_test)

    For more use cases see `the label relations exploration guide <../labelrelations.ipynb>`_.

    """

    def __init__(self, graph_builder, method):
        """Initializes the clusterer

        Attributes
        ----------
        graph_builder: a GraphBuilderBase inherited transformer
                Class used to provide an underlying graph for NetworkX
        """
        super(NetworkXLabelGraphClusterer, self).__init__(graph_builder)
        self.method = method

    def fit_predict(self, X, y):
        """Performs clustering on y and returns list of label lists

        Builds a label graph using the provided graph builder's `transform` method
        on `y` and then detects communities using the selected `method`.

        Sets :code:`self.weights_` and :code:`self.graph_`.

        Parameters
        ----------
        X : None
            currently unused, left for scikit compatibility
        y : scipy.sparse
            label space of shape :code:`(n_samples, n_labels)`

        Returns
        -------
        arrray of arrays of label indexes (numpy.ndarray)
            label space division, each sublist represents labels that are in that community
        """
        edge_map = self.graph_builder.transform(y)

        if self.graph_builder.is_weighted:
            self.weights_ = dict(weight=list(edge_map.values()))
        else:
            self.weights_ = dict(weight=None)

        self.graph_ = nx.Graph()
        for n in range(y.shape[1]):
            self.graph_.add_node(n)

        for e, w in edge_map.items():
            self.graph_.add_edge(e[0], e[1], weight=w)

        if self.method == 'louvain':
            partition_dict = community.best_partition(self.graph_)
        else:
            partition_dict = nx.asyn_lpa_communities(self.graph_, 'weight')

        return np.array(
            _membership_to_list_of_communities(
                [
                    partition_dict[i] for i in range(y.shape[1])
                ],
                1+max(partition_dict.values())
            )
        )