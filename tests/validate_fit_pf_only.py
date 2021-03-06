""" Fit a model with cirrhosis CSMR data and assumptions on remission
and excess-mortality"""

import pylab as pl
import pymc as mc
import pandas
import networkx as nx

# add to path, to make importing possible
import sys
sys.path += ['.', '..']

import data
import consistent_model
import fit_model
import covariate_model
import graphics


# load the model from disk, and adjust the data and parameters for this example
model = data.ModelData.from_gbd_json('/var/tmp/dismod_working/test/dm-19807/json/dm-19807.json')

model.parameters['p']['parameter_age_mesh'] = range(0,101,20)

model.parameters['pf'] = {}
model.parameters['pf']['parameter_age_mesh'] = range(0,101,20)

model.parameters['r']['level_value'] = dict(age_before=100, age_after=100, value=0.)
model.parameters['f']['level_value'] = dict(age_before=100, age_after=100, value=2.)



# no covariates
model.input_data = model.input_data.drop([col for col in model.input_data.columns if col.startswith('x_')], axis=1)


# create model for (latin_america_central, male, 2005)
root_area = 'latin_america_central'
subtree = nx.traversal.bfs_tree(model.hierarchy, root_area)
relevant_rows = [i for i, r in model.input_data.T.iteritems() \
                     if r['area'] in subtree \
                     and r['year_end'] >= 1997 \
                     and r['sex'] in ['male', 'total']]
model.input_data = model.input_data.ix[relevant_rows]


## create and fit consistent model at gbd region level
vars = consistent_model.consistent_model(model, root_area=root_area, root_sex='male', root_year=2005, priors={})
posterior_model = fit_model.fit_consistent_model(vars, iter=3003, burn=1500, thin=10, tune_interval=100)


## generate estimates for latin_america_central, male, 2005
predict_area = root_area
posteriors = {}
for t in 'i r f p rr pf'.split():
    posteriors[t] = pl.median(covariate_model.predict_for(model.output_template, model.hierarchy,
                                                root_area, 'male', 2005,
                                                predict_area, 'male', 2005, vars[t]), axis=0)

graphics.all_plots(model, vars, {}, posteriors)
