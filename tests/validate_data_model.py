""" Test data model

These tests are use randomized computation, so they might fail
occasionally due to stochastic variation
"""

# matplotlib will open windows during testing unless you do the following
import matplotlib
matplotlib.use("AGG")

# add to path, to make importing possible
import sys
sys.path += ['.', '..']

import pylab as pl
import pymc as mc
import pandas
import networkx as nx

import data
import data_model
reload(data_model)

def test_data_model_sim():
    # generate simulated data
    n = 50
    sigma_true = .025

    # start with truth
    a = pl.arange(0, 100, 1)
    pi_age_true = .0001 * (a * (100. - a) + 100.)

    # choose age intervals to measure
    age_start = pl.array(mc.runiform(0, 100, n), dtype=int)
    age_start.sort()  # sort to make it easy to discard the edges when testing
    age_end = pl.array(mc.runiform(age_start+1, pl.minimum(age_start+10,100)), dtype=int)

    # find truth for the integral across the age intervals
    import scipy.integrate
    pi_interval_true = [scipy.integrate.trapz(pi_age_true[a_0i:(a_1i+1)]) / (a_1i - a_0i) 
                        for a_0i, a_1i in zip(age_start, age_end)]

    # generate covariates that add explained variation
    X = mc.rnormal(0., 1.**2, size=(n,3))
    beta_true = [-.1, .1, .2]
    Y_true = pl.dot(X, beta_true)

    # calculate the true value of the rate in each interval
    pi_true = pi_interval_true*pl.exp(Y_true)

    # simulate the noisy measurement of the rate in each interval
    p = mc.rnormal(pi_true, 1./sigma_true**2.)

    # store the simulated data in a pandas DataFrame
    data = pandas.DataFrame(dict(value=p, age_start=age_start, age_end=age_end,
                                 x_0=X[:,0], x_1=X[:,1], x_2=X[:,2]))
    data['effective_sample_size'] = pl.maximum(p*(1-p)/sigma_true**2, 1.)

    data['standard_error'] = pl.nan
    data['upper_ci'] = pl.nan
    data['lower_ci'] = pl.nan

    data['year_start'] = 2005.  # TODO: make these vary
    data['year_end'] = 2005.
    data['sex'] = 'total'
    data['area'] = 'all'

    # generate a moderately complicated hierarchy graph for the model
    hierarchy = nx.DiGraph()
    hierarchy.add_node('all')
    hierarchy.add_edge('all', 'super-region-1', weight=.1)
    hierarchy.add_edge('super-region-1', 'NAHI', weight=.1)
    hierarchy.add_edge('NAHI', 'CAN', weight=.1)
    hierarchy.add_edge('NAHI', 'USA', weight=.1)
    output_template=pandas.DataFrame(dict(year=[1990, 1990, 2005, 2005, 2010, 2010]*2,
                                          sex=['male', 'female']*3*2,
                                          x_0=[.5]*6*2,
                                          x_1=[0.]*6*2,
                                          x_2=[.5]*6*2,
                                          pop=[50.]*6*2,
                                          area=['CAN']*6 + ['USA']*6))
    

    # create model and priors
    vars = data_model.data_model('test', data, hierarchy, 'all')


    # fit model
    mc.MAP(vars).fit(method='fmin_powell', verbose=1)
    m = mc.MCMC(vars)
    m.use_step_method(mc.AdaptiveMetropolis, [m.gamma_bar, m.gamma, m.beta])
    m.sample(30000, 15000, 15)

    # check estimates
    pi_usa = data_model.predict_for(output_template, hierarchy, 'all', 'USA', 'male', 1990, vars)
    assert pl.allclose(pi_usa.mean(), (m.mu_age.trace()*pl.exp(.05)).mean(), rtol=.1)

    # check convergence
    print 'gamma mc error:', m.gamma_bar.stats()['mc error'].round(2), m.gamma.stats()['mc error'].round(2)


    # plot results
    for a_0i, a_1i, p_i in zip(age_start, age_end, p):
        pl.plot([a_0i, a_1i], [p_i,p_i], 'rs-', mew=1, mec='w', ms=4)
    pl.plot(a, pi_age_true, 'g-', linewidth=2)
    pl.plot(pl.arange(101), m.mu_age.stats()['mean'], 'k-', drawstyle='steps-post', linewidth=3)
    pl.plot(pl.arange(101), m.mu_age.stats()['95% HPD interval'], 'k', linestyle='steps-post:')
    pl.plot(pl.arange(101), pi_usa.mean(0), 'r-', linewidth=2, drawstyle='steps-post')
    pl.savefig('age_integrating_sim.png')

    # compare estimate to ground truth (skip endpoints, because they are extra hard to get right)
    assert pl.allclose(m.pi.stats()['mean'][10:-10], pi_true[10:-10], rtol=.2)
    lb, ub = m.pi.stats()['95% HPD interval'].T
    assert pl.mean((lb <= pi_true)[10:-10] & (pi_true <= ub)[10:-10]) > .75

    

if __name__ == '__main__':
    import nose
    nose.runmodule()
    
