# special-invention
Method to setup and run a self organizing neural network on a quantum computer for personalized drug discovery

The Quantum Universal Exchange Language (Q-UEL) based on Dirac notation and algebra from quantum mechanics, along with its associated data mining and Hyperbolic Dirac Net (HDN) for probabilistic inference, has proven to be a useful architectural principle for knowledge management, analysis and prediction systems in medicine.

The development of a new drug is an extremely laborious and time-consuming process. Thus, quite early on, computer methods have been used to further an understanding of
the interactions of a drug with its receptor. Molecular modelling and rational drug design have become indispensable tools for the development of a new drug. Recently, combinatorial chemistry and high-throughput screening have been introduced in order to
speed up the drug development process. These methods produce massive amounts of data that have to be analyzed in an efficient manner in order to make best use of these
novel methods. We will show here that self-organizing neural networks, such as the one introduced by Kohonen, can be used both in rational drug design and in combinatorial chemistry.
The application of neural networks in chemistry has increased dramatically in recent years. In a Kohonen neural network, the artificial neurons self-organize in
an unsupervised learning process and, thus, can be used to generate topological feature maps. It will be shown here that this potential can be utilized to analyze the shape and
surface properties of those three-dimensional objects responsible for biological activity, molecules. 

Q-UEL vs Predecessors:

Q-UEL is not a major international standards effort, and currently, researchers tend to look to linked data formats based on SW technologies. These include Resource Description Framework (RDF), Web Ontology Language (OWL), Simple Knowledge Organization System
(SKOS), and SPARQL . Others look to the original XML, often also considered as a tool of the Semantic Web (SW), but in any case attractive for linking information on the World Wide Web (WWW). The PRISMA approach to structured systematic reviews in medicine and for epidemiology should be mentioned because Q-UEL has also been used for that purpose. However, for certain interoperability aspects of PRISMA, it was found that an XML solution was more useful [9]. Bayes nets [3] and
its causal model have been also expressed in XML.


None of the main tools of the SW are extensively intrinsically probabilistic, although there have been diverse proposals, many of which are based on the BN expressed in XML. That is unfortunate. Not only does uncertainty abound in medicine but probabilities, or measures based on them, are needed as the basis of important metrics in evidence based medicine (and in epidemiology and public health generally). In effect, a physician is concerned with the probabilities that particular diseases are currently the best interpretation of the symptoms and clinical laboratory results (differential diagnosis), with the risk of specified diseases occurring in the future (risk factors, prognoses), with most probable causes (etiology), and with finding the therapeutic intervention that provides the probable opportunities for success.

The pharmaceutical industry is concerned with selecting for development the drug candidates that will most probably succeed. Genomics usually introduces a whole new probabilistic element. Common inherited diseases often represent a complex interaction of many genes,involving control systems affected by past environment and therapeutic interventions. While for some diseases like sickle cell anemia and cystic fibrosis detection of one inherited mutation in each copy of DNA from
the parents is a very persuasive indicator, mutations such as BRCA1 and BRCA2 represent a risk, not guarantee, of breast cancer, and absence of these mutations does not guarantee avoidance. 

Such probabilistic outcome is similarly most commonly the case for other cancers, and cardiovascular, diabetic, behavioral, and many other disorders. The Bayes Net is probabilistic, but as a basis for probabilistic knowledge in the SW and clinical decision support it has other limitations. It is possible that the total adoption of BN-based methods as a standard for medicine have been impeded by controversy over the interpretation of BNs as a Directed Acyclic Graph (DAG) of probabilistic knowledge, originally justified by a causal model that is subject to some criticism. The DAG used to represent a net of probabilistic knowledge seems inconsistent with querying by a set (not ordered list) of tuples, with classical statistics and its adage that “Correlation does not imply causation” [14], the physics of bidirectional transitions in nature (e.g. Ref. [15]), and not least with the
spirit of the WWW and SW that emphasize connectedness and a general “Web of Data consisting of all sorts of data types and forms”. The HDN allows the Bidirectional General Graph (BGG). 


In these specific method and application, there is a one-to-one mapping of a single molecule into a single Kohonen network. However, a Kohonen network can also be used for the analysis of datasets of molecules, where several molecules are simultaneously mapped into one Kohonen network. In order to make full use of the potential of self-organizing networks, novel representations of molecular structures have been developed. These
methods can be put into a clear hierarchy, starting from molecular topology going all the way to molecular surfaces. They do not only encode structural information, but also information on the properties of atoms or of molecular surfaces. 



References
[1] B. Robson, O.K. Baek, The Engines of Hippocrates. From the Dawn of Medicine to Medical and Pharmaceutical Informatics, Wiley, 2009.
[2] B. Robson, J. Garnier, Introduction to Proteins and Protein Engineering, Elsevier, 1988.
[3] J. Pearl, Bayesian networks: a model of self-activated memory for evidential reasoning (UCLA technical report CSD-850017), in: Proceedings of the 7th Conference of the Cognitive Science Society, University of California, Irvine, CA, 1985, pp. 329–334.
[4] B. Robson, Hyperbolic Dirac nets for medical decision support. Theory, methods, and comparison with BNs, Comput. Biol. Med. 51 (2014) 183–197.
[5] B. Robson, Bidirectional general graphs for inference. Principles and implications for medicine, Comput. Biol. Med. 108 (2019) 382–399.
[6] S. Deckelman, B. Robson, Split-complex numbers and Dirac bra-kets, Commun. Inf. Syst. 14 (3) (2015) 135–149.
[7] B.Robson,P.T.Caruso,U.J.Balis,Suggestionsforawebbaseduniversalexchange and inference language for medicine, Comput. Biol. Med. 43 (12) (2013), 229- 2310.
[8] G.S. Ginsbirg, H.F. Willard, Genomic and Precision Medicine. Foundations, Translation, and Implementation, Elsevier Inc., 2017.
[9] M. Alloghani, D. Al-Jumeily, A. Hussain, A.J. Aljaaf, J. Mustafina, M. Khalaf, S. Y. Tan, The XML and semantic web: a systematic review on technologies, international conference Big data analytics, data mining and computational intelligence (last accessed 9/18/2019), http://www.iadisportal.org/digital-l ibrary/the-xml-and-semantic-web-a-systematic-review-on-technologies, 2019.
