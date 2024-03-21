#export SCRAM_ARCH=slc7_amd64_gcc900
#git clone https://github.com/mmrowietz/CmsPmssm
#cmsrel CMSSW_12_2_4
#cd CMSSW_12_2_4/src/
#cmsenv
#cd ../../CmsPmssm
#python3 pmssm.py -i /eos/cms/store/group/phys_susy/pMSSMScan/MasterTrees/pmssmtree_11aug2023.root -o plots


from ROOT import *
import os,sys
from utils import *
import argparse
import numpy as np


# terms defining
terms = {}
terms["higgsino"] = "(Re_N_13**2+Re_N_14**2)"
terms["bino"] = "Re_N_11**2"
terms["wino"] = "Re_N_12**2"

#constraints relating to the analyses likelihoods and others
theconstraints = {}
theconstraints["reason"] = "(!(xsec_tot_pb>1E3 && Zsig_combined==0))" # this excludes points with enormous weights that could not be excluded, almost certaintly due to these large weights and statistical chance
theconstraints["reason_simplified"] = "(!(xsec_tot_pb>1E3 && Zsig_combined_simplified==0))"# this excludes points with enormous weights that could not be excluded, almost certaintly due to these large weights and statistical chance
theconstraints["reweight"] = "(1/PickProbability)" #this reweights each point to remove the effect of over-sampling and under-sampling. Important for Bayesian interpretation of results that require a meaningful prior.

#The following are Bayes factors using simplified or (where available) full combine likelihoods
#*_100s is the likelihood assuming a signal strength of 1, *_050s assumes a signal strength of 0.5, *_150s assumes a signal strength of 1.5, and *_0s assumes no signal (SM-only likelihood)
theconstraints["cms_sus_19_006"] = "(exp(llhd_cms_sus_19_006_100s-llhd_cms_sus_19_006_0s))"
theconstraints["cms_sus_19_006_down"] = "(exp(llhd_cms_sus_19_006_050s-llhd_cms_sus_19_006_0s))"
theconstraints["cms_sus_19_006_up"] = "(exp(llhd_cms_sus_19_006_150s-llhd_cms_sus_19_006_0s))"

theconstraints["cms_sus_18_004_simplified"] = "(exp(llhd_cms_sus_18_004_100s-llhd_cms_sus_18_004_0s))"
theconstraints["cms_sus_18_004_simplified_down"] = "(exp(llhd_cms_sus_18_004_050s-llhd_cms_sus_18_004_0s))"
theconstraints["cms_sus_18_004_simplified_up"] = "(exp(llhd_cms_sus_18_004_150s-llhd_cms_sus_18_004_0s))"

#At some point we switches to saving the Bayes factor directly in the tree, instead of the signal and signal-less likelihoods
#Here, muXpYf refers to signal strength of X.Y, and f refers to "full" as in full combine likelihood. The max sometimes has to be taken because root can't handle extremely small floats.
theconstraints["cms_sus_18_004"] = "(max(bf_cms_sus_18_004_mu1p0f,1E-5))"
theconstraints["cms_sus_18_004_down"] = "max((bf_cms_sus_18_004_mu0p5f,1E-5))"
theconstraints["cms_sus_18_004_up"] = "max((bf_cms_sus_18_004_mu1p5f,1E-5))"

theconstraints["cms_sus_21_007"] = "(exp(llhd_cms_sus_21_007_100s-llhd_cms_sus_21_007_0s))"
theconstraints["cms_sus_21_007_down"] = "(exp(llhd_cms_sus_21_007_050s-llhd_cms_sus_21_007_0s))"
theconstraints["cms_sus_21_007_up"] = "(exp(llhd_cms_sus_21_007_150s-llhd_cms_sus_21_007_0s))"

theconstraints["cms_sus_21_007_simplified"] = "(exp(llhd_cms_sus_21_007_100s-llhd_cms_sus_21_007_0s))"
theconstraints["cms_sus_21_007_simplified_down"] = "(exp(llhd_cms_sus_21_007_050s-llhd_cms_sus_21_007_0s))"
theconstraints["cms_sus_21_007_simplified_up"] = "(exp(llhd_cms_sus_21_007_150s-llhd_cms_sus_21_007_0s))"


theconstraints["atlas_susy_2018_32"] = "(exp(llhd_atlas_susy_2018_32_100s-llhd_atlas_susy_2018_32_0s))"
theconstraints["atlas_susy_2018_32_down"] = "(exp(llhd_atlas_susy_2018_32_150s-llhd_atlas_susy_2018_32_0s))"
theconstraints["atlas_susy_2018_32_up"] = "(exp(llhd_atlas_susy_2018_32_050s-llhd_atlas_susy_2018_32_0s))"

theconstraints["atlas_susy_2018_06"] = "(exp(llhd_atlas_susy_2018_06_100s-llhd_atlas_susy_2018_06_0s))"
theconstraints["atlas_susy_2018_06_down"] = "(exp(llhd_atlas_susy_2018_06_050s-llhd_atlas_susy_2018_06_0s))"
theconstraints["atlas_susy_2018_06_up"] = "(exp(llhd_atlas_susy_2018_06_150s-llhd_atlas_susy_2018_06_0s))"

theconstraints["cms_sus_21_006_simplified"] = "(exp(llhd_cms_sus_21_006_100s-llhd_cms_sus_21_006_0s))"
theconstraints["cms_sus_21_006_simplified_down"] = "(exp(llhd_cms_sus_21_006_050s-llhd_cms_sus_21_006_0s))"
theconstraints["cms_sus_21_006_simplified_up"] = "(exp(llhd_cms_sus_21_006_150s-llhd_cms_sus_21_006_0s))"

theconstraints["cms_sus_21_006"] = "(max(bf_cms_sus_21_006_mu1p0f,1E-5))"
theconstraints["cms_sus_21_006_down"] = "(max(bf_cms_sus_21_006_mu1p0f,1E-5))"
theconstraints["cms_sus_21_006_up"] = "(max(bf_cms_sus_21_006_mu1p0f,1E-5))"


#this part combines the various analysis Bayes factors, once including full combine likelihoods where possible, and once using only counts-based simplified likelihoods
#This sums up the likelihoods assuming the different signal strengths, and the SM-only likelihoods. The sum does not include the analyses where the Bayes factor is saved in the tree instead of the likelihoods
signals = "+".join(["llhd_cms_sus_19_006_100s","llhd_atlas_susy_2018_32_100s","llhd_atlas_susy_2018_06_100s"])
signals_down = "+".join(["llhd_cms_sus_19_006_050s","llhd_atlas_susy_2018_32_050s","llhd_atlas_susy_2018_06_050s"])
signals_up = "+".join(["llhd_cms_sus_19_006_150s","llhd_atlas_susy_2018_32_150s","llhd_atlas_susy_2018_06_150s"])
_backgrounds = "+".join(["llhd_cms_sus_19_006_0s","llhd_atlas_susy_2018_32_0s","llhd_atlas_susy_2018_06_0s"])
#Because we switched to saving Bayes factors, this became a little more complicated
#again, the max is taken because ROOT has problems with small floats

bfs = []
bfs_down = []
bfs_up = []
bfs.append("(max(bf_cms_sus_21_006_mu1p0f,1E-20))")
bfs_down.append("(max(bf_cms_sus_21_006_mu0p5f,1E-20))")
bfs_up.append("(max(bf_cms_sus_21_006_mu1p5f,1E-20))")
bfs.append("(max(bf_cms_sus_18_004_mu1p0f,1E-20))")
bfs_down.append("(max(bf_cms_sus_18_004_mu0p5f,1E-20))")
bfs_up.append("(max(bf_cms_sus_18_004_mu1p5f,1E-20))")


bfs_no_cms_sus_21_006 = []
bfs_no_cms_sus_21_006_down = []
bfs_no_cms_sus_21_006_up = []
bfs_no_cms_sus_21_006.append("(max(bf_cms_sus_18_004_mu1p0f,1E-20))")
bfs_no_cms_sus_21_006_down.append("(max(bf_cms_sus_18_004_mu0p5f,1E-20))")
bfs_no_cms_sus_21_006_up.append("(max(bf_cms_sus_18_004_mu1p5f,1E-20))")

bfs_no_cms_sus_18_004 = []
bfs_no_cms_sus_18_004_down = []
bfs_no_cms_sus_18_004_up = []
bfs_no_cms_sus_18_004.append("(max(bf_cms_sus_21_006_mu1p0f,1E-20))")
bfs_no_cms_sus_18_004_down.append("(max(bf_cms_sus_21_006_mu0p5f,1E-20))")
bfs_no_cms_sus_18_004_up.append("(max(bf_cms_sus_21_006_mu1p5f,1E-20))")

#We only started storing the Bayes factors for the full combine likelihoods, so the simplified version is simpler
signals_simplified = "+".join(["llhd_cms_sus_19_006_100s","llhd_atlas_susy_2018_32_100s","llhd_atlas_susy_2018_06_100s","llhd_cms_sus_21_006_100s","llhd_cms_sus_18_004_100s"])
signals_simplified_down = "+".join(["llhd_cms_sus_19_006_050s","llhd_atlas_susy_2018_32_050s","llhd_atlas_susy_2018_06_050s","llhd_cms_sus_21_006_050s","llhd_cms_sus_18_004_050s"])
signals_simplified_up = "+".join(["llhd_cms_sus_19_006_150s","llhd_atlas_susy_2018_32_150s","llhd_atlas_susy_2018_06_150s","llhd_cms_sus_21_006_150s","llhd_cms_sus_18_004_150s"])
_backgrounds_simplified = "+".join(["llhd_cms_sus_19_006_0s","llhd_atlas_susy_2018_32_0s","llhd_atlas_susy_2018_06_0s","llhd_cms_sus_21_006_0s","llhd_cms_sus_18_004_0s"])

#these are the Bayes factors for the combination of all analyses. The first term handles the analyses where the log likelihood is stored, the second term handles the analyses where the Bayes factor is stored in the tree 
theconstraints["combined"] = "(exp(("+signals+")-("+_backgrounds+"))*"+"*".join(bfs)+")"
theconstraints["combined_simplified"] = "(exp(("+signals_simplified+")-("+_backgrounds_simplified+")))"
#some useful constraints
theconstraints["pure higgsino"] = "("+terms["higgsino"]+">0.95)"
theconstraints["pure wino"] = "("+terms["wino"]+">0.95)"
theconstraints["pure bino"] = "("+terms["bino"]+">0.95)"

theconstraints["bino-wino mix"] = "(!("+"||".join([theconstraints["pure bino"],theconstraints["pure wino"],theconstraints["pure higgsino"]])+") && "+terms["bino"]+">"+terms["higgsino"]+" && "+terms["bino"]+">"+terms["wino"]+")"
theconstraints["bino-higgsino mix"] = "(!("+"||".join([theconstraints["pure bino"],theconstraints["pure wino"],theconstraints["pure higgsino"]])+") && "+terms["bino"]+">"+terms["wino"]+" && "+terms["higgsino"]+">"+terms["wino"]+")"
theconstraints["wino-higgsino mix"] = "(!("+"||".join([theconstraints["pure bino"],theconstraints["pure wino"],theconstraints["pure higgsino"]])+") && "+terms["bino"]+"<"+terms["wino"]+" && "+terms["bino"]+"<"+terms["higgsino"]+")"



#z-axis colors
sprobcontours = np.float64([-0.01,1E-5,0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95,1-1E-5,1.01])
custompalette = []
cols = TColor.GetNumberOfColors()# This gets the colors of the Palette currently set in ROOT
#This part sets bins with a survival probability of zero (less than second entry of sprobcontours list to be exact) to Black color. Bins with a survival probability of exactly 1 (greater than second last entry of sprobcontours list) to Grey.
for i in range(cols):
    if i<19: # The exact i was found by trial and error. Sorry.
        col = kBlack
    elif i > 253:
        col = kGray
    else:
        col = TColor.GetColorPalette(i) # This part keeps the color from the currently set palette
        
    custompalette.append(col)
custompalette = np.intc(custompalette)

#dictionary mapping the z-scores for the different analyses to the tree branches 
branchnames = {}
for analysis in ["cms_sus_19_006","cms_sus_21_006","cms_sus_18_004","atlas_susy_2018_32","atlas_susy_2018_06","combined","cms_sus_21_006_simplified","cms_sus_21_007","cms_sus_21_007_simplified"]:
    branchnames[analysis] = {}
    branchnames[analysis+"_up"] = {}
    branchnames[analysis+"_down"] = {}
    #now do the defaults
    if analysis in ["cms_sus_18_004","cms_sus_21_006"]:
        branchnames[analysis]["Z"] = "Zsig_"+analysis+"_mu1p0f"
        branchnames[analysis+"_up"]["Z"] = "Zsig_"+analysis+"_mu1p5f"
        branchnames[analysis+"_down"]["Z"] = "Zsig_"+analysis+"_mu0p5f"
    elif analysis == "combined_simplified":
        branchnames[analysis]["Z"] = "Zsig_"+analysis
    else:
        branchnames[analysis]["Z"] = "Zsig_"+analysis.replace("_simplified","")
        branchnames[analysis+"_up"]["Z"] = "Zsig_"+analysis.replace("_simplified","")+"_15s"
        branchnames[analysis+"_down"]["Z"] = "Zsig_"+analysis.replace("_simplified","")+"_05s"



def get_impact_plots(localtree, analysis, hname, xtitle, xbins, xlow, xup, _logx, drawstring, moreconstraints=[],
                     moreconstraints_prior=False):
    """
    This creates an impact plot. Returns dictionary with four histograms: the prior, posterior, as well as the +-50% cross section versions of the posterior.
    @param localtree: Function needs to be passed the ROOT tree from which to operate
    @param analysis: The analysis to use for LHC constraints. Can be any string for which a dictionary entry and corresponding ROOT branch exists in "branchnames". Currently does not allow for arbitrary combinations of analyses
    @param hname: Name of the returned histogram
    @param xtitle: x-axis label
    @param xbins: number of x-axis bins
    @param xlow: lower edge of zero'th bin
    @param xup: upper edge of xbins's bin
    @param _logx: sets x-axis to logarithmic (base 10). If you use this, use linear Y:X in drawstring, not Y:log(X)
    @param drawstring: Draw string passed to root .Draw() function, of the form Y:X, where Y is drawn on the y-axis and X is drawn on the x-axis. Accepts tree branches and mathematical operations acted on them, such as for example log(Y):10*X.
    @param moreconstraints: list of logical expressions that constrain the tree. Can use tree branches and mathematical operations. Each constrain in the list is logically multiplied
    @param moreconstraints_prior: list of logical expressions that should apply to the prior. Default is to NOT apply constraints on the prior. Can use tree branches and mathematical operations. Each constrain in the list is logically multiplied
    """
    if "simplified" in analysis:  # reweighting is always done, in addition to removing unreasonable points
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason_simplified"]])
        constraintstring_prior = "*".join([theconstraints["reweight"], theconstraints["reason_simplified"]])
    else:
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason"]])
        constraintstring_prior = "*".join([theconstraints["reweight"], theconstraints["reason"]])
    for newc in moreconstraints:
        constraintstring += "*(" + newc + ")"
    if moreconstraints_prior:
        for newc_p in moreconstraints_prior:
            constraintstring_prior += "*(" + newc_p + ")"

    # get the scales to normalize all histograms to one
    htest = TH1F("scale", "", 1000, -1000, 1000)
    localtree.Draw("PickProbability>>" + htest.GetName(), constraintstring_prior)
    prior_scalar = 1. / htest.Integral(-1, 9999999)
    htest.Delete()
    htest = TH1F("scale", "", 1000, -1000, 1000)
    localtree.Draw("PickProbability>>" + htest.GetName(),
                   "*".join([constraintstring, "(" + branchnames[analysis]["Z"] + ">-1.64)"]))
    posterior_scalar = 1. / htest.Integral(-1, 9999999)
    htest.Delete()
    htest = TH1F("scale", "", 1000, -1000, 1000)
    localtree.Draw("PickProbability>>" + htest.GetName(),
                   "*".join([constraintstring, "(" + branchnames[analysis + "_up"]["Z"] + ">-1.64)"]))
    posterior_scalar_up = 1. / htest.Integral(-1, 9999999)
    htest.Delete()
    htest = TH1F("scale", "", 1000, -1000, 1000)
    localtree.Draw("PickProbability>>" + htest.GetName(),
                   "*".join([constraintstring, "(" + branchnames[analysis + "_down"]["Z"] + ">-1.64)"]))
    posterior_scalar_down = 1. / htest.Integral(-1, 9999999)
    htest.Delete()

    # debug me!
    maxy = -1
    prior = mkhistlogx("prior", "", xbins, xlow, xup, logx=_logx)
    posterior = mkhistlogx(hname, "", xbins, xlow, xup, logx=_logx)  # prior.Clone(hname)
    posterior_up = mkhistlogx(hname + "_up", "", xbins, xlow, xup, logx=_logx)  # prior.Clone(hname+"_up")
    posterior_down = mkhistlogx(hname + "_down", "", xbins, xlow, xup, logx=_logx)  # prior.Clone(hname+"_down")
    localtree.Draw(drawstring + ">>" + prior.GetName(), constraintstring_prior)
    localtree.Draw(drawstring + ">>" + posterior.GetName(),
                   "*".join([constraintstring, "(" + branchnames[analysis]["Z"] + ">-1.64)"]))
    localtree.Draw(drawstring + ">>" + posterior_up.GetName(),
                   "*".join([constraintstring, "(" + branchnames[analysis + "_up"]["Z"] + ">-1.64)"]))
    localtree.Draw(drawstring + ">>" + posterior_down.GetName(),
                   "*".join([constraintstring, "(" + branchnames[analysis + "_down"]["Z"] + ">-1.64)"]))

    histoStyler(prior, kBlue - 9, fill=True)
    histoStyler(posterior, kBlack)
    histoStyler(posterior_down, kRed, linestyle=kDashed)
    histoStyler(posterior_up, kMagenta, linestyle=kDashed)
    prior.Scale(prior_scalar)
    posterior.Scale(posterior_scalar)
    posterior_up.Scale(posterior_scalar_up)
    posterior_down.Scale(posterior_scalar_down)
    maxy = max([prior.GetMaximum(), posterior.GetMaximum(), posterior_down.GetMaximum(), posterior_up.GetMaximum()])
    prior.GetYaxis().SetRangeUser(0, 1.1 * maxy)
    prior.GetXaxis().SetTitle(xtitle)
    posterior.GetYaxis().SetRangeUser(0, 1.1 * maxy)
    posterior.GetXaxis().SetTitle(xtitle)
    posterior_up.GetYaxis().SetRangeUser(0, 1.1 * maxy)
    posterior_up.GetXaxis().SetTitle(xtitle)
    posterior_down.GetYaxis().SetRangeUser(0, 1.1 * maxy)
    posterior_down.GetXaxis().SetTitle(xtitle)
    prior.GetYaxis().SetTitle("pMSSM density")
    posterior.GetYaxis().SetTitle("pMSSM density")
    posterior_up.GetYaxis().SetTitle("pMSSM density")
    posterior_down.GetYaxis().SetTitle("pMSSM density")

    return {"prior": prior, "posterior": posterior, "posterior_up": posterior_up, "posterior_down": posterior_down}


def get_quantile_plot_1D(localtree, analysis, hname, xtitle, xbins, xlow, xup, _logx, drawstring, moreconstraints=[],
                         quantiles=[0.]):
    """
    This creates a 1D survival probability plot. Returns dictionary with N Bayes factor quantile histograms, one for each of the N quantiles given.
    @param localtree: Function needs to be passed the ROOT tree from which to operate

    @param analysis: The analysis to use for LHC constraints. Can be any string for which a dictionary entry and corresponding ROOT branch exists in "branchnames". Currently does not allow for arbitrary combinations of analyses
    @param hname: Name of the returned histogram
    @param xtitle: x-axis label
    @param xbins: number of x-axis bins
    @param xlow: lower edge of zero'th bin
    @param xup: upper edge of xbins's bin
    @param _logx: sets x-axis to logarithmic (base 10). If you use this, use linear Y:X in drawstring, not Y:log(X)
    @param drawstring: Draw string passed to root .Draw() function, of the form Y:X, where Y is drawn on the y-axis and X is drawn on the x-axis. Accepts tree branches and mathematical operations acted on them, such as for example log(Y):10*X.
    @param moreconstraints: list of logical expressions that constrain the tree. Can use tree branches and mathematical operations. Each constrain in the list is logically multiplied
    @param moreconstraints_prior: list of logical expressions that should apply to the prior. Default is to NOT apply constraints on the prior. Can use tree branches and mathematical operations. Each constrain in the list is logically multiplied
    @param quantiles: list of quantiles to produce. Also accepts a single integer of float.
    """
    _drawstring = theconstraints[analysis] + ":" + drawstring
    if "simplified" in analysis:  # reweighting is always done, in addition to removing unreasonable points
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason_simplified"]])
    else:
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason"]])
    for newc in moreconstraints:
        constraintstring += "*(" + newc + ")"
    _quantiles = []
    if type(quantiles) in [list, tuple]:
        for qt in quantiles:
            if qt > 1:
                _quantiles.append(qt / 100.)
            elif qt > 0:
                _quantiles.append(qt)
            else:
                print("Invalid quantile provided, please use positive values")
                exit()
    elif type(quantiles) in [int, float]:
        if quantiles > 1:
            _quantiles.append(quantiles / 100.)
        elif quantiles > 0:
            _quantiles.append(quantiles)
        else:
            print("Invalid quantile provided, please use positive values")
            exit()

    else:
        print("invalid type of quantile given, please provide either an int or float, or a list of ints or floats")
        exit()
    probs = list(np.array([x]) for x in _quantiles)
    qs = list(np.array([0.]) for x in _quantiles)

    hists = {}
    qhist = mkhistlogxy("qhist", "", xbins, xlow, xup, 3000, 0, 30, logy=False, logx=_logx)
    localtree.Draw(_drawstring + ">>" + qhist.GetName(), constraintstring, "")
    htemplate = qhist.ProfileX('OF UF')
    xax = htemplate.GetXaxis()
    for prob in probs:
        hists["quantile_" + str(int(100 * prob))] = htemplate.ProjectionX().Clone("quantile_" + str(int(100 * prob)))
        hists["quantile_" + str(int(100 * prob))].Reset()
    for ibinx in range(1, xax.GetNbins() + 1):
        hz = qhist.ProjectionY('hz', ibinx, ibinx)
        try:
            hz.Scale(1.0 / hz.Integral(-1, 99999))
        except:
            for hname, hist in hists.items():
                hist.SetBinContent(ibinx, 0)
            continue
        quantiles = []
        for ix, prob in enumerate(probs):
            quantiles.append(hz.GetQuantiles(1, qs[ix], prob))
            hists["quantile_" + str(int(100 * prob))].SetBinContent(ibinx, qs[ix][0])

    for histname, hist in hists.items():
        histoStyler(hist)
        hist.GetYaxis().SetRangeUser(0, 1.1 * hist.GetMaximum())
        hist.GetYaxis().SetTitle("Bayes factor")
        hist.GetXaxis().SetTitle(xtitle)

    return hists


def get_SP_plot_1D(localtree, analysis, hname, xtitle, xbins, xlow, xup, _logx, drawstring, moreconstraints=[],
                   moreconstraints_prior=False):
    """
    This creates a 1D survival probability plot. Returns dictionary with three survival probability histograms, assuming the nominal signal cross sections, as well as the +-50% signal cross sections.
    @param localtree: Function needs to be passed the ROOT tree from which to operate
    @param analysis: The analysis to use for LHC constraints. Can be any string for which a dictionary entry and corresponding ROOT branch exists in "branchnames". Currently does not allow for arbitrary combinations of analyses
    @param hname: Name of the returned histogram
    @param xtitle: x-axis label
    @param xbins: number of x-axis bins
    @param xlow: lower edge of zero'th bin
    @param xup: upper edge of xbins's bin
    @param _logx: sets x-axis to logarithmic (base 10). If you use this, use linear Y:X in drawstring, not Y:log(X)
    @param drawstring: Draw string passed to root .Draw() function, of the form Y:X, where Y is drawn on the y-axis and X is drawn on the x-axis. Accepts tree branches and mathematical operations acted on them, such as for example log(Y):10*X.
    @param moreconstraints: list of logical expressions that constrain the tree. Can use tree branches and mathematical operations. Each constrain in the list is logically multiplied
    @param moreconstraints_prior: list of logical expressions that should apply to the prior. Default is to NOT apply constraints on the prior. Can use tree branches and mathematical operations. Each constrain in the list is logically multiplied
    """
    if "simplified" in analysis:  # reweighting is always done, in addition to removing unreasonable points
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason_simplified"]])
        constraintstring_prior = "*".join([theconstraints["reweight"], theconstraints["reason_simplified"]])
    else:
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason"]])
        constraintstring_prior = "*".join([theconstraints["reweight"], theconstraints["reason"]])
    for newc in moreconstraints:
        constraintstring += "*(" + newc + ")"
    if moreconstraints_prior:
        for newc_p in moreconstraints_prior:
            constraintstring_prior += "*(" + newc_p + ")"

    maxy = -1
    prior = mkhistlogx("prior", "", xbins, xlow, xup, logx=_logx)
    posterior = mkhistlogx(hname, "", xbins, xlow, xup, logx=_logx)
    posterior_up = mkhistlogx(hname + "_up", "", xbins, xlow, xup, logx=_logx)
    posterior_down = mkhistlogx(hname + "_down", "", xbins, xlow, xup, logx=_logx)

    localtree.Draw(drawstring + ">>" + prior.GetName(), constraintstring_prior, "")
    localtree.Draw(drawstring + ">>" + posterior.GetName(),
                   "*".join([constraintstring, "(" + branchnames[analysis]["Z"] + ">-1.64)"]), "")
    localtree.Draw(drawstring + ">>" + posterior_up.GetName(),
                   "*".join([constraintstring, "(" + branchnames[analysis + "_up"]["Z"] + ">-1.64)"]), "")
    localtree.Draw(drawstring + ">>" + posterior_down.GetName(),
                   "*".join([constraintstring, "(" + branchnames[analysis + "_down"]["Z"] + ">-1.64)"]), "")
    histoStyler(posterior, kBlack)
    histoStyler(posterior_up, kMagenta, linestyle=kDashed)
    histoStyler(posterior_down, kRed, linestyle=kDashed)
    posterior.Divide(prior)
    posterior_up.Divide(prior)
    posterior_down.Divide(prior)

    maxy = max([posterior.GetMaximum(), posterior_up.GetMaximum(), posterior_down.GetMaximum()])
    posterior.GetYaxis().SetRangeUser(0, maxy + 0.1)
    posterior.GetXaxis().SetTitle(xtitle)
    posterior_up.GetYaxis().SetRangeUser(0, maxy + 0.1)
    posterior_up.GetXaxis().SetTitle(xtitle)
    posterior_down.GetYaxis().SetRangeUser(0, maxy + 0.1)
    posterior_down.GetXaxis().SetTitle(xtitle)
    posterior.GetYaxis().SetTitle("survival probability")
    return {"posterior": posterior, "posterior_up": posterior_up, "posterior_down": posterior_down}


def get_SP_plot_2D(localtree, analysis, hname, xtitle, xbins, xlow, xup, ytitle, ybins, ylow, yup, _logx, _logy,
                   drawstring, moreconstraints=[], moreconstraints_prior=False):
    """
    This creates a 2D survival probability plot
    @param localtree: Function needs to be passed the ROOT tree from which to operate
    @param analysis: The analysis to use for LHC constraints. Can be any string for which a dictionary entry and corresponding ROOT branch exists in "branchnames". Currently does not allow for arbitrary combinations of analyses
    @param hname: Name of the returned histogram
    @param xtitle: x-axis label
    @param xbins: number of x-axis bins
    @param xlow: lower edge of zero'th bin
    @param xup: upper edge of xbins's bin
    @param ytitle: y-axis label
    @param ybins: number of y-axis bins
    @param ylow: lower edge of zero'th bin
    @param yup: upper edge of ybins's bin
    @param _logx: sets x-axis to logarithmic (base 10). If you use this, use linear Y:X in drawstring, not Y:log(X)
    @param _logy: sets y-axis to logarithmic (base 10). If you use this, use linear Y:X in drawstring, not log(Y):X
    @param drawstring: Draw string passed to root .Draw() function, of the form Y:X, where Y is drawn on the y-axis and X is drawn on the x-axis. Accepts tree branches and mathematical operations acted on them, such as for example log(Y):10*X.
    @param moreconstraints: list of logical expressions that constrain the tree. Can use tree branches and mathematical operations. Each constrain in the list is logically multiplied
    @param moreconstraints_prior: list of logical expressions that should apply to the prior. Default is to NOT apply constraints on the prior. Can use tree branches and mathematical operations. Each constrain in the list is logically multiplied
    """
    hdenom = mkhistlogxy("hdenom", '', xbins, xlow, xup, ybins, ylow, yup, logx=_logx, logy=_logy)
    hret = hdenom.Clone(
        hname)  # this makes sure that the denominator and the numerator histograms are identically set up
    hret.SetContour(len(sprobcontours) - 1, sprobcontours)  # this defines the z-axis color palette and tick length
    if "simplified" in analysis:  # reweighting is always done, in addition to removing unreasonable points
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason_simplified"]])
        constraintstring_prior = "*".join([theconstraints["reweight"], theconstraints["reason_simplified"]])
    else:
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason"]])
        constraintstring_prior = "*".join([theconstraints["reweight"], theconstraints["reason"]])
    for newc in moreconstraints:
        constraintstring += "*(" + newc + ")"
    if moreconstraints_prior:
        for newc_p in moreconstraints_prior:
            constraintstring_prior += "*(" + newc_p + ")"

    localtree.Draw(drawstring + ">>" + hdenom.GetName(), constraintstring_prior, "colz")
    localtree.Draw(drawstring + ">>" + hret.GetName(),
                   "*".join([constraintstring, "(" + branchnames[analysis]["Z"] + ">-1.64)"]), "colz")
    hret.GetZaxis().SetRangeUser(-0.001, 1)
    cutoff = 1E-3
    hret.GetZaxis().SetTitle("survival probability")
    hret.Divide(hdenom)
    for i in range(1, hret.GetNbinsX() + 1):
        for j in range(1, hret.GetNbinsY() + 1):
            if hret.GetBinContent(i, j) == 0 and hdenom.GetBinContent(i, j) > 0:
                hret.SetBinContent(i, j, 0)
            elif hret.GetBinContent(i, j) == 0 and hdenom.GetBinContent(i, j) == 0:
                hret.SetBinContent(i, j, -1)
            elif hret.GetBinContent(i, j) < cutoff and hdenom.GetBinContent(i, j) > 0:
                hret.SetBinContent(i, j, cutoff)
    # always run gStyle.SetPalette(len(custompalette),custompalette) when drawing SP, otherwise gStyle.SetPalette(kBird) or other preferred Palette
    # gStyle.SetNumberContours(999)
    histoStyler(hret)
    hret.GetXaxis().SetTitle(xtitle)
    hret.GetYaxis().SetTitle(ytitle)
    hret.GetZaxis().SetTitle("survival probability")
    hret.SetContour(len(sprobcontours) - 1, sprobcontours)
    return hret


def get_quantile_plot_2D(localtree, quantile, analysis, hname, xtitle, xbins, xlow, xup, ytitle, ybins, ylow, yup,
                         _logx, _logy, drawstring, moreconstraints=[], moreconstraints_prior=False):
    """
    This creates a Bayes factor quantile plot
    @param localtree: Function needs to be passed the ROOT tree from which to operate
    @param quantile: The quantile of the Bayes factor to use
    @param analysis: The analysis to use for LHC constraints. Can be any string for which a dictionary entry exists in theconstraints dictionary. Currently does not allow for arbitrary combinations of analyses
    @param hname: Name of the returned histogram
    @param xtitle: x-axis label
    @param xbins: number of x-axis bins
    @param xlow: lower edge of zero'th bin
    @param xup: upper edge of xbins's bin
    @param ytitle: y-axis label
    @param ybins: number of y-axis bins
    @param ylow: lower edge of zero'th bin
    @param yup: upper edge of ybins's bin
    @param _logx: sets x-axis to logarithmic (base 10). If you use this, use linear Y:X in drawstring, not Y:log(X)
    @param _logy: sets y-axis to logarithmic (base 10). If you use this, use linear Y:X in drawstring, not log(Y):X
    @param drawstring: Draw string passed to root .Draw() function, of the form Y:X, where Y is drawn on the y-axis and X is drawn on the x-axis. Accepts tree branches and mathematical operations acted on them, such as for example log(Y):10*X.
    @param moreconstraints: list of logical expressions that constrain the tree. Can use tree branches and mathematical operations. Each constrain in the list is logically multiplied
    @param moreconstraints_prior: list of logical expressions that should apply to the prior. Default is to NOT apply constraints on the prior. Can use tree branches and mathematical operations. Each constrain in the list is logically multiplied
    """

    # quantile is percentile/100
    if quantile > 1:
        _quantile = quantile / 100.
    elif quantile > 0:
        _quantile = quantile
    else:
        print("Invalid quantile provided, please use positive values")
        exit()

    _drawstring = theconstraints[analysis] + ":" + drawstring
    prob = np.array([quantile])
    q = np.array([0.])
    htemp = mkhistlogxyz("htemp", '', xbins, xlow, xup, ybins, ylow, yup, 3000, 0, 30, logx=_logx, logy=_logy,
                         logz=False)

    if "simplified" in analysis:  # reweighting is always done, in addition to removing unreasonable points
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason_simplified"]])
        constraintstring_prior = "*".join([theconstraints["reweight"], theconstraints["reason_simplified"]])
    else:
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason"]])
        constraintstring_prior = "*".join([theconstraints["reweight"], theconstraints["reason"]])
    for newc in moreconstraints:
        constraintstring += "*(" + newc + ")"
    if moreconstraints_prior:
        for newc_p in moreconstraints_prior:
            constraintstring_prior += "*(" + newc_p + ")"

    prior = mkhistlogxy("prior", '', xbins, xlow, xup, ybins, ylow, yup, logx=_logx, logy=_logy)
    localtree.Draw(drawstring + ">>" + prior.GetName(), constraintstring_prior, "")
    localtree.Draw(_drawstring + ">>" + htemp.GetName(), constraintstring, "")

    # create hist, fill it?
    htemplate = htemp.Project3DProfile('yx UF OF')
    xax, yax = htemplate.GetXaxis(), htemplate.GetYaxis()
    returnhist = htemplate.ProjectionXY().Clone(hname)
    returnhist.Reset()
    cutoff = 1E-3

    for ibinx in range(1, xax.GetNbins() + 1):
        for ibiny in range(1, yax.GetNbins() + 1):
            hz = htemp.ProjectionZ('hz', ibinx, ibinx, ibiny, ibiny)
            try:
                hz.Scale(1.0 / hz.Integral())
            except:
                returnhist.SetBinContent(ibinx, ibiny, 0)
                continue
            quant = hz.GetQuantiles(1, q, prob)
            returnhist.SetBinContent(ibinx, ibiny, q[0])
    zaxis_max = -1
    for i in range(1, returnhist.GetNbinsX() + 1):
        for j in range(1, returnhist.GetNbinsY() + 1):
            if returnhist.GetBinContent(i, j) == 0 and prior.GetBinContent(i, j) > 0:
                returnhist.SetBinContent(i, j, 0)
            elif returnhist.GetBinContent(i, j) == 0 and prior.GetBinContent(i, j) == 0:
                returnhist.SetBinContent(i, j, -1)
            elif returnhist.GetBinContent(i, j) < cutoff and prior.GetBinContent(i, j) > 0:
                returnhist.SetBinContent(i, j, cutoff)
            zaxis_max = max(zaxis_max, returnhist.GetBinContent(i, j))
    returnhist.GetZaxis().SetRangeUser(-0.001, max(1, zaxis_max + 0.1))
    # gStyle.SetNumberContours(999)
    returnhist.SetTitle("")
    returnhist.GetXaxis().SetTitle(xtitle)
    returnhist.GetYaxis().SetTitle(ytitle)
    returnhist.GetZaxis().SetTitle(str(int(100 * quantile)) + "th percentile Bayes factor")
    histoStyler(returnhist)
    return returnhist


def getThresholdForContainment(hist, intervals):
    """
    Returns the thresholds for the given credibility intervals
    @param hist: Histogram from which to generate the thresholds
    @param intervals: list of credibility intervals for which to generate the thresholds
    """
    # interval needs to be sorted from low to high
    contents = []
    thresholds = []  # returned thresholds corresponding to asked containment intervals
    total = 0
    # sort the bin contentss in descending order
    for xbin in range(hist.GetNbinsX() + 1):
        for ybin in range(hist.GetNbinsY() + 1):
            val = hist.GetBinContent(xbin, ybin)
            if val >= 0:
                contents.append(val)
                total += val
    contents.sort(reverse=True)

    threshold = 0
    intervalix = 0
    for ix, val in enumerate(contents):
        threshold += val
        if threshold >= intervals[intervalix] * total:
            thresholds.append(val)
            intervalix += 1
            if intervalix == len(intervals):
                break
    thresholds.sort()
    return thresholds


def get_prior_CI(localtree, hname, xbins, xlow, xup, ybins, ylow, yup, _logx, _logy, drawstring, moreconstraints=[],
                 intervals=[0.1, 0.67, 0.95], contourcolors=[kRed, kRed + 2, kMagenta],
                 contourstyle=[kSolid, kSolid, kSolid]):
    """
    Produce credibility intervals for the prior, defined here as the smallest number of bins that contain X% of the prior density.
    Returns the contours for the given intervals
    @param localtree: Function needs to be passed the ROOT tree from which to operate
    @param hname: Name of the returned histogram
    @param xbins: number of x-axis bins. The choice of binning can have some impact on the shape of the credibility intervals
    @param xlow: lower edge of zero'th bin. The axis ranges should always encompass ALL model points
    @param xup: upper edge of xbins's bin. The axis ranges should always encompass ALL model points
    @param ybins: number of y-axis bins
    @param ylow: lower edge of zero'th bin. The axis ranges should always encompass ALL model points
    @param yup: upper edge of ybins's bin. The axis ranges should always encompass ALL model points
    @param _logx: sets x-axis to logarithmic (base 10). If you use this, use linear Y:X in drawstring, not Y:log(X)
    @param _logy: sets y-axis to logarithmic (base 10). If you use this, use linear Y:X in drawstring, not log(Y):X
    @param drawstring: Draw string passed to root .Draw() function, of the form Y:X, where Y is drawn on the y-axis and X is drawn on the x-axis. Accepts tree branches and mathematical operations acted on them, such as for example log(Y):10*X. This should always be the same as the underlying histogram
    @param moreconstraints: list of logical expressions that constrain the tree. Can use tree branches and mathematical operations. Each constrain in the list is logically multiplied. For the prior, this should usually be empty.
    @param intervals: List of X% prior credibility intervals to produce if possible
    @param contourcolors: Specifies the colors for the contours. Must be a list of the same length as the intervals.
    @param contourstyle: Specifies the line style for the contours. Must be a list of the same length as the intervals.
    
    """
    if "simplified" in analysis:  # reweighting is always done, in addition to removing unreasonable points
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason_simplified"]])
    else:
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason"]])
    for newc in moreconstraints:
        constraintstring += "*(" + newc + ")"

    contours = mkhistlogxy(hname, '', xbins, xlow, xup, ybins, ylow, yup, logx=_logx, logy=_logy)
    localtree.Draw(drawstring + ">>" + contours.GetName(), constraintstring, "cont2")
    contarrays = np.array(getThresholdForContainment(contours, intervals))
    # redraw the histogram with cont list option
    localtree.Draw(drawstring + ">>" + contours.GetName(), constraintstring, "cont list")
    # optionally smooth the histogram, as the exact boundary is not important and this makes the intervals look nicer
    contours.Smooth()
    contours.SetContour(len(contarrays),
                        contarrays)  # this produces the contours for the thresholds given in contarrays
    the_contours = {}
    gPad.Update()
    conts = gROOT.GetListOfSpecials().FindObject("contours")
    for ix, contlist in enumerate(conts):
        the_contours[intervals[len(intervals) - ix - 1]] = []
        for cont in contlist:
            if cont.GetN() < 5: continue  # optionally only consider contours that are somewhat large
            cont.SetLineColor(contourcolors[ix])
            cont.SetMarkerColor(contourcolors[ix])
            cont.SetLineStyle(contourstyle[ix])
            cont.SetLineWidth(3)
            the_contours[intervals[len(intervals) - ix - 1]].append(cont.Clone())
    return the_contours


def get_posterior_CI(localtree, analysis, hname, xbins, xlow, xup, ybins, ylow, yup, _logx, _logy, drawstring,
                     moreconstraints=[], intervals=[0.1, 0.67, 0.95], contourcolors=[kRed, kRed + 2, kMagenta],
                     contourstyle=[kDashed, kDashed, kDashed]):
    """
    Produce credibility intervals for the prior, defined here as the smallest number of bins that contain X% of the prior density.
    Returns the contours for the given intervals
    @param localtree: Function needs to be passed the ROOT tree from which to operate
    @param analysis: The analysis to use for LHC constraints. Can be any string for which a dictionary entry and corresponding ROOT branch exists in "branchnames". Currently does not allow for arbitrary combinations of analyses
    @param hname: Name of the returned histogram
    @param xbins: number of x-axis bins. The choice of binning can have some impact on the shape of the credibility intervals
    @param xlow: lower edge of zero'th bin. The axis ranges should always encompass ALL model points
    @param xup: upper edge of xbins's bin. The axis ranges should always encompass ALL model points
    @param ybins: number of y-axis bins
    @param ylow: lower edge of zero'th bin. The axis ranges should always encompass ALL model points
    @param yup: upper edge of ybins's bin. The axis ranges should always encompass ALL model points
    @param _logx: sets x-axis to logarithmic (base 10). If you use this, use linear Y:X in drawstring, not Y:log(X)
    @param _logy: sets y-axis to logarithmic (base 10). If you use this, use linear Y:X in drawstring, not log(Y):X
    @param drawstring: Draw string passed to root .Draw() function, of the form Y:X, where Y is drawn on the y-axis and X is drawn on the x-axis. Accepts tree branches and mathematical operations acted on them, such as for example log(Y):10*X. This should always be the same as the underlying histogram
    @param moreconstraints: list of logical expressions that constrain the tree. Can use tree branches and mathematical operations. Each constrain in the list is logically multiplied. For the prior, this should usually be empty.
    @param intervals: List of X% prior credibility intervals to produce if possible
    @param contourcolors: Specifies the colors for the contours. Must be a list of the same length as the intervals.
    @param contourstyle: Specifies the line style for the contours. Must be a list of the same length as the intervals.
    
    """
    if "simplified" in analysis:  # reweighting is always done, in addition to removing unreasonable points
        constraintstring = "*".join(
            [theconstraints["reweight"], theconstraints["reason_simplified"], theconstraints[analysis]])
    else:
        constraintstring = "*".join([theconstraints["reweight"], theconstraints["reason"], theconstraints[analysis]])
    for newc in moreconstraints:
        constraintstring += "*(" + newc + ")"

    contours = mkhistlogxy(hname, '', xbins, xlow, xup, ybins, ylow, yup, logx=_logx, logy=_logy)
    localtree.Draw(drawstring + ">>" + contours.GetName(), constraintstring, "cont2")
    contarrays = np.array(getThresholdForContainment(contours, intervals))
    # redraw the histogram with cont list option
    localtree.Draw(drawstring + ">>" + contours.GetName(), constraintstring, "cont list")
    # optionally smooth the histogram, as the exact boundary is not important and this makes the intervals look nicer
    contours.Smooth()
    contours.SetContour(len(contarrays),
                        contarrays)  # this produces the contours for the thresholds given in contarrays
    the_contours = {}
    gPad.Update()
    conts = gROOT.GetListOfSpecials().FindObject("contours")
    for ix, contlist in enumerate(conts):
        the_contours[intervals[len(intervals) - ix - 1]] = []
        for cont in contlist:
            if cont.GetN() < 5: continue  # optionally only consider contours that are somewhat large
            cont.SetLineColor(contourcolors[ix])
            cont.SetMarkerColor(contourcolors[ix])
            cont.SetLineStyle(contourstyle[ix])
            cont.SetLineWidth(3)
            the_contours[intervals[len(intervals) - ix - 1]].append(cont.Clone())
    return the_contours


def ScaleAxis(axis, scale_function):
    if axis.GetXbins().GetSize():
        # Variable bin sizes
        X = TArrayD(axis.GetXbins())
        for i in range(X.GetSize()):
            X[i] = scale_function(X[i])
        axis.Set(X.GetSize() - 1, X.GetArray())
    else:
        # Fixed bin sizes
        axis.Set(axis.GetNbins(), scale_function(axis.GetXmin()), scale_function(axis.GetXmax()))


def scaleXaxis(histogram,scaleFactor=1.0):
    x_axis = histogram.GetXaxis()

    ScaleAxis(x_axis,lambda x: x / scaleFactor)

def scaleYaxis(histogram,scaleFactor=1.0):
    y_axis = histogram.GetYaxis()

    ScaleAxis(y_axis,lambda y: y / scaleFactor)

class PMSSM:
    def __init__(self,intree,outdir):
        if outdir[-1]!="/":
                outdir+="/"
        if not os.path.exists(outdir):
                os.system("mkdir -p "+outdir)
        self.canvas = mkcanvas("canvas")
        self.intree = intree
        self.outdir = outdir

        gPad.SetRightMargin(0.15) #optional
        gPad.SetLeftMargin(0.15) #optional
        self.legend = mklegend(0.2,0.8,0.85,0.99) #optional, can also use default constructor below
        gStyle.SetPalette(len(custompalette),custompalette)#We do this because we are only drawing survival probability plots
    
    def SP_plot_2D(self,outname, analysis, hname, xaxis, yaxis,
                   drawstring, moreconstraints=[], moreconstraints_prior=False,
                   prior= False, posterior = False
                   ):

        '''
        prior = {
            hname: "hname",
            xaxis: {}, 
            yaxis: {},
            drawstring: "",
            moreconstraints=[],
            intervals = [0.1, 0.67, 0.95],
            contourcolors=[kRed, kRed + 2, kMagenta],
            contourstyle=[kSolid, kSolid, kSolid]
        }

        posterior = {
            analysis: "analysis",
            hname: "hname",
            xaxis: {}, 
            yaxis: {},
            drawstring: "",
            moreconstraints=[],
            intervals = [0.1, 0.67, 0.95],
            contourcolors=[kRed, kRed + 2, kMagenta],
            contourstyle=[kSolid, kSolid, kSolid]
        }

        '''

        xtitle = xaxis.get("title",None)
        xbins = xaxis.get("bins",100)
        xlow, xup = xaxis.get("interval",[None,None])
        _logx = xaxis.get("logScale",False)
        xscalefactor = xaxis.get("linearScale",1.0)

        ytitle = yaxis.get("title",None)
        ybins = yaxis.get("bins",100)
        ylow, yup = yaxis.get("interval",[None,None])
        _logy = yaxis.get("logScale",False)
        yscalefactor = yaxis.get("linearScale",1.0)


        hist = get_SP_plot_2D(
            localtree=self.intree,
            analysis = analysis,
            hname = hname,
            xtitle = xtitle,
            xbins = xbins,
            xlow = xlow,
            xup = xup,
            ytitle = ytitle,
            ybins = ybins,
            ylow = ylow,
            yup = yup,
            _logx = _logx,
            _logy = _logy,
            drawstring = drawstring,
            moreconstraints = moreconstraints,
            moreconstraints_prior = moreconstraints_prior)
        
        if xscalefactor != 1.0:
            scaleXaxis(hist,scaleFactor=xscalefactor)
        if yscalefactor != 1.0:
            scaleYaxis(hist,scaleFactor=yscalefactor)
        
        hist.Draw("colz")

        ##get_prior_CI

        if prior:

            priorconts = self.prior_CI(
                hname = prior.get("hname",""),
                xaxis = prior.get("xaxis"),
                yaxis = prior.get("yaxis"),
                drawstring = prior.get("drawstring"),
                moreconstraints = prior.get("moreconstraints",[]),
                intervals = prior.get("intervals",[0.1, 0.67, 0.95]),
                contourcolors = prior.get("contourcolors",[kRed, kRed + 2, kMagenta]),
                contourstyle = prior.get("contourstyle",[kSolid, kSolid, kSolid]))

            for ix,interval in enumerate(priorconts):
                for cont in priorconts[interval]:
                    cont.Draw("same")
        
        ##get_posterior_CI

        if posterior: 

            posteriorconts = self.posterior_CI(
                analysis =  posterior.get("analysis","combined"),
                hname = posterior.get("hname",""),
                xaxis = posterior.get("xaxis"),
                yaxis = posterior.get("yaxis"),
                drawstring = posterior.get("drawstring"), 
                moreconstraints = posterior.get("moreconstraints",[]),
                intervals = posterior.get("intervals",[0.1, 0.67, 0.95]),
                contourcolors = posterior.get("contourcolors",[kRed, kRed + 2, kMagenta]),
                contourstyle = posterior.get("contourstyle",[kSolid, kSolid, kSolid])
            )

            for ix,interval in enumerate(posteriorconts):
                for cont in posteriorconts[interval]:
                    cont.Draw("same")

        if prior and posterior:
            for ix,interval in enumerate(priorconts):
                if len(priorconts[interval])>0:
                    self.legend.AddEntry(priorconts[interval][0],str(int(100*(interval)))+"%  prior CI","l",)
                if len(posteriorconts[interval])>0:
                    self.legend.AddEntry(posteriorconts[interval][0],str(int(100*(interval)))+"% posterior CI","l",)
            self.legend.SetNColumns(2)
            self.legend.Draw("same")
    
        self.canvas.SaveAs(self.outdir+outname+".png")
        self.legend.Clear()
        self.legend.SetNColumns(1)
        hist.Delete()


    def prior_CI (self, hname, xaxis, yaxis,
                    drawstring, moreconstraints=[],
                    intervals = [0.1, 0.67, 0.95],
                    contourcolors=[kRed, kRed + 2, kMagenta],
                    contourstyle=[kSolid, kSolid, kSolid]):

            xbins = xaxis.get("bins",100)
            xlow, xup = xaxis.get("interval",[None,None])
            _logx = xaxis.get("logScale",False)
            xscalefactor = xaxis.get("linearScale",1.0)

            ybins = yaxis.get("bins",100)
            ylow, yup = yaxis.get("interval",[None,None])
            _logy = yaxis.get("logScale",False)
            yscalefactor = yaxis.get("linearScale",1.0)

            hist = get_prior_CI(
                localtree=self.intree,
                hname = hname,
                xbins = xbins,
                xlow = xlow,
                xup = xup,
                ybins = ybins,
                ylow = ylow,
                yup = yup,
                _logx = _logx,
                _logy = _logy,
                drawstring = drawstring,
                moreconstraints = moreconstraints,
                intervals = intervals,
                contourcolors = contourcolors,
                contourstyle = contourstyle
                )

            for cont_val in hist:
                    cont_graphs = hist[cont_val]
                    for cont in cont_graphs:
                        if xscalefactor != 1.0:
                            scaleXaxis(cont,scaleFactor=xscalefactor)
                        if yscalefactor != 1.0:
                            scaleYaxis(cont,scaleFactor=yscalefactor)

            return hist

    def posterior_CI(self, analysis, hname, xaxis, yaxis,
                   drawstring, moreconstraints=[], intervals=[0.1, 0.67, 0.95], contourcolors=[kRed, kRed + 2, kMagenta],
                     contourstyle=[kDashed, kDashed, kDashed]):

        xbins = xaxis.get("bins",100)
        xlow, xup = xaxis.get("interval",[None,None])
        _logx = xaxis.get("logScale",False)
        xscalefactor = xaxis.get("linearScale",1.0)

        ybins = yaxis.get("bins",100)
        ylow, yup = yaxis.get("interval",[None,None])
        _logy = yaxis.get("logScale",False)
        yscalefactor = yaxis.get("linearScale",1.0)


        hist = get_posterior_CI(
            localtree=self.intree,
            analysis = analysis,
            hname = hname,
            xbins = xbins,
            xlow = xlow,
            xup = xup,
            ybins = ybins,
            ylow = ylow,
            yup = yup,
            _logx = _logx,
            _logy = _logy,
            drawstring = drawstring,
            moreconstraints = moreconstraints,
            intervals = intervals,
            contourcolors = contourcolors,
            contourstyle = contourstyle)
        

        for cont_val in hist:
            cont_graphs = hist[cont_val]
            for cont in cont_graphs:
                if xscalefactor != 1.0:
                    scaleXaxis(cont,scaleFactor=xscalefactor)
                if yscalefactor != 1.0:
                    scaleYaxis(cont,scaleFactor=yscalefactor)

        return hist



def run(args):
    #setup
    infile = TFile(args.input)
    intree=infile.Get("mcmc")
    outdir = args.outdir

    pmssm_plotter = PMSSM(intree = intree, outdir=outdir)
    # gluino

    pmssm_plotter.SP_plot_2D(
        outname="gluino_chi10",
        analysis="combined",
        hname="gluino_chi10",
        xaxis = {
            "title": "m(#tilde{g}) [TeV]",
            "bins" : 100,
            "interval":[0,10000],
            "logScale": False,
            "linearScale": 1000.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "abs(chi10):g",
        moreconstraints = [],
        moreconstraints_prior = False
        )
    
    pmssm_plotter.SP_plot_2D(
        outname="gluino_chi10_contoured",
        analysis="combined",
        hname="gluino_chi10",
        xaxis = {
            "title": "m(#tilde{g}) [GeV]",
            "bins" : 100,
            "interval":[0,10000],
            "logScale": False,
            "linearScale": 1.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [GeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1.0 
        },
        drawstring = "abs(chi10):g",
        prior = {
            "hname": "gluino_chi10_priorcontours",
            "xaxis": {
                "bins": 100,
                "interval": [0,10000],
                "logScale": False,
                "linearScale": 1.0
            }, 
            "yaxis": {
                "bins": 60,
                "interval": [0,3000],
                "logScale": False,
                "linearScale": 1.0
            },
            "drawstring": "abs(chi10):g",
        },
        posterior = {
            "analysis": "combined",
            "hname" : "gluino_chi10_priorcontours",
            "xaxis": {
                "bins": 100,
                "interval": [0,10000],
                "logScale": False,
                "linearScale": 1.0
            }, 
            "yaxis": {
                "bins": 60,
                "interval": [0,3000],
                "logScale": False,
                "linearScale": 1.0
            },
            "drawstring": "abs(chi10):g",
        },
        moreconstraints = [],
        moreconstraints_prior = False,
        )

    # top quark
    pmssm_plotter.SP_plot_2D(
        outname="stop_chi10",
        analysis="combined",
        hname="stop_chi10",
        xaxis = {
            "title": "m(#tilde{t}_{1}) [TeV]",
            "bins" : 100,
            "interval":[0,10000],
            "logScale": False,
            "linearScale": 1000.0 #1/1000.0
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "abs(chi10):t1",
        moreconstraints = [],
        moreconstraints_prior = False
        )
    

    pmssm_plotter.SP_plot_2D(
        outname="stop_chi10_higgsino",
        analysis="combined",
        hname="stop_chi10",
        xaxis = {
            "title": "m(#tilde{t}_{1}) [TeV]",
            "bins" : 100,
            "interval":[0,10000],
            "logScale": False,
            "linearScale": 1000.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "abs(chi10):t1",
        moreconstraints = ["(Re_N_13**2+Re_N_14**2)>0.95"],
        moreconstraints_prior = False
        )
    
    pmssm_plotter.SP_plot_2D(
        outname="stop_chi10_higgsino_RDPlanck",
        analysis="combined",
        hname="stop_chi10",
        xaxis = {
            "title": "m(#tilde{t}_{1}) [TeV]",
            "bins" : 100,
            "interval":[0,10000],
            "logScale": False,
            "linearScale": 1000.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "abs(chi10):t1",
        moreconstraints = ["(Re_N_13**2+Re_N_14**2)>0.95","abs(Omegah2-0.12)<=0.012"],
        moreconstraints_prior = False
        )
    
    # bottom squark

    pmssm_plotter.SP_plot_2D(
        outname="sbottom_chi10",
        analysis="combined",
        hname="sbottom_chi10",
        xaxis = {
            "title": "m(#tilde{b}_{1}) [TeV]",
            "bins" : 100,
            "interval":[0,10000],
            "logScale": False,
            "linearScale": 1000.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "abs(chi10):b1",
        moreconstraints = [],
        moreconstraints_prior = False
        )
    
    pmssm_plotter.SP_plot_2D(
        outname="sbottom_chi10_higgsino",
        analysis="combined",
        hname="sbottom_chi10",
        xaxis = {
            "title": "m(#tilde{b}_{1}) [TeV]",
            "bins" : 100,
            "interval":[0,10000],
            "logScale": False,
            "linearScale": 1000.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "abs(chi10):b1",
        moreconstraints = ["(Re_N_13**2+Re_N_14**2)>0.95"],
        moreconstraints_prior = False
        )
    
    pmssm_plotter.SP_plot_2D(
        outname="sbottom_chi10_higgsino_RDPlanck",
        analysis="combined",
        hname="sbottom_chi10",
        xaxis = {
            "title": "m(#tilde{b}_{1}) [TeV]",
            "bins" : 100,
            "interval":[0,10000],
            "logScale": False,
            "linearScale": 1000.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "abs(chi10):b1",
        moreconstraints = ["(Re_N_13**2+Re_N_14**2)>0.95","abs(Omegah2-0.12)<=0.012"],
        moreconstraints_prior = False
        )

    # lcsp

    pmssm_plotter.SP_plot_2D(
        outname="lcsp_chi10",
        analysis="combined",
        hname="lcsp_chi10",
        xaxis = {
            "title": "m(LCSP) [TeV]",
            "bins" : 100,
            "interval":[0,10000],
            "logScale": False,
            "linearScale": 1000.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "abs(chi10):lcsp",
        moreconstraints = [],
        moreconstraints_prior = False
        )

    pmssm_plotter.SP_plot_2D(
        outname="lcsp_chi10_higgsino",
        analysis="combined",
        hname="lcsp_chi10",
        xaxis = {
            "title": "m(LCSP) [TeV]",
            "bins" : 100,
            "interval":[0,10000],
            "logScale": False,
            "linearScale": 1000.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "abs(chi10):lcsp",
        moreconstraints = ["(Re_N_13**2+Re_N_14**2)>0.95"],
        moreconstraints_prior = False
        )

    pmssm_plotter.SP_plot_2D(
        outname="lcsp_chi10_higgsino_RDPlanck",
        analysis="combined",
        hname="lcsp_chi10",
        xaxis = {
            "title": "m(LCSP) [TeV]",
            "bins" : 100,
            "interval":[0,10000],
            "logScale": False,
            "linearScale": 1000.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "abs(chi10):lcsp",
        moreconstraints = ["(Re_N_13**2+Re_N_14**2)>0.95","abs(Omegah2-0.12)<=0.012"],
        moreconstraints_prior = False
        )

    #deltaM

    pmssm_plotter.SP_plot_2D(
        outname="deltaM_chi10",
        analysis="combined",
        hname="deltaM_chi10",
        xaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{#pm}_{1}-#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 100,
            "interval":[0,8000],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "lcsp:abs(chi1pm-chi10)",
        moreconstraints = [],
        moreconstraints_prior = False
        )
    
    pmssm_plotter.SP_plot_2D(
        outname="deltaM_chi10_higgsino",
        analysis="combined",
        hname="deltaM_chi10",
        xaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{#pm}_{1}-#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 100,
            "interval":[0,8000],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "lcsp:abs(chi1pm-chi10)",
        moreconstraints = ["(Re_N_13**2+Re_N_14**2)>0.95"],
        moreconstraints_prior = False
        )

    pmssm_plotter.SP_plot_2D(
        outname="deltaM_chi10_higgsino_RDPlanck",
        analysis="combined",
        hname="deltaM_chi10",
        xaxis = {
            "title": "m(#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 50,
            "interval":[0,2500],
            "logScale": False,
            "linearScale": 1000.0 
        },
        yaxis = {
            "title": "m(#tilde{#chi}^{#pm}_{1}-#tilde{#chi}^{0}_{1}) [TeV]",
            "bins" : 100,
            "interval":[0,8000],
            "logScale": False,
            "linearScale": 1000.0 
        },
        drawstring = "lcsp:abs(chi1pm-chi10)",
        moreconstraints = ["(Re_N_13**2+Re_N_14**2)>0.95","abs(Omegah2-0.12)<=0.012"],
        moreconstraints_prior = False
        )


if __name__ == "__main__":
    gROOT.SetBatch(True)
    gStyle.SetOptStat(0)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i","--input",default = "/eos/cms/store/group/phys_susy/pMSSMScan/MasterTrees/pmssmtree_11aug2023.root",help="Specify the tree containing the points for which you want the survival probability plots")
    parser.add_argument("-o","--outdir",required = True,help="Specify the output directory")
#    parser.add_argument("-z","--ztypes",choices=["survival_probability","quantile_Bayesfactor_50","quantile_Bayesfactor_90""quantile_Bayesfactor_98","standard"],help="Specify the types of z-axis quantity",action="append",required = True)
    #parser.add_argument("-a","--analyses",choices=["cms_sus_19_006","atlas_susy_2018_32","atlas_susy_2018_06","cms_sus_21_006","cms_sus_21_007","cms_sus_21_007_simplified","cms_sus_18_004","combined","all","all_simplified","combined_simplified","cms_sus_18_004_simplified","cms_sus_21_006_simplified"],help="Specify the analyses for which the plots should be made",action="append",required = True)
    args = parser.parse_args()
    run(args)