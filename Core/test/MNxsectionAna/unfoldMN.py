#!/usr/bin/env python

import ROOT
ROOT.gROOT.SetBatch(True)
from ROOT import *

import os,re,sys,math

import CommonFSQFramework.Core.Util
import CommonFSQFramework.Core.Style

from array import array

from optparse import OptionParser

ROOT.gSystem.Load("libRooUnfold.so")
from HistosHelper import getHistos


from mnDraw import DrawMNPlots 

alaGri = False
odir = ""
ntoys = 10
def vary1d(h):
    for ix in xrange(0, h.GetNbinsX()+2): # vary also over/under flow bins
            val = h.GetBinContent(ix)
            if val == 0: continue
            err = h.GetBinError(ix)
            if err == 0: 
                print "Warning: err=0 in {} bin {} with val={}".format(histo.GetName(), ix, val)
            mod = ROOT.gRandom.Gaus(0, err)
            print mod
            newVal = val+mod
            newErr = err # should we scale here?
            if newVal <= 0: newVal, newErr = 0,0
            h.SetBinContent(ix, newVal)
            h.SetBinError(ix, newErr)
    return h

# TODO: what with over flows here?
def vary2d(h):
    for ix in xrange(0, h.GetNbinsX()+2): # vary also over/under flow bins
        for iy in xrange(0, h.GetNbinsY()+2): # vary also over/under flow bins
            val = h.GetBinContent(ix, iy)
            if val == 0: continue
            err = h.GetBinError(ix, iy)
            if err == 0: 
                print "Warning: err=0 in {} bin {},{} with val={}".format(histo.GetName(), ix, iy, val)
            mod = ROOT.gRandom.Gaus(0, err)
            print mod
            newVal = val+mod
            newErr = err # should we scale here?
            if newVal <= 0: newVal, newErr = 0,0
            h.SetBinContent(ix, iy, newVal)
            h.SetBinError(ix, iy, newErr)

    return h


def vary(histo):
    #print "RAN", ROOT.gRandom.Gaus(0, 1)
    if "TH1" in histo.ClassName():
        return vary1d(histo)
    elif "TH2" in histo.ClassName():
        return vary2d(histo)
    else:
        raise Exception("vary: unsupported object {} {}".format(histo.ClassName(), histo.GetName()))


def doUnfold(measured, rooresponse):
    if alaGri:
        # histos[baseMC][r] - response object
        # histo - detector level distribution
        #   RooUnfoldResponse(const TH1* measured, const TH1* truth, const TH2* response
        for i in xrange(0, measured.GetNbinsX()+1):
            denom = rooresponse.Hmeasured().GetBinContent(i)
            if denom == 0: continue
            nom = rooresponse.Hfakes().GetBinContent(i)
            if nom > denom:
                print "Warning! More fakes than meas", nom, denom
            factor = 1.-nom/denom
            val = measured.GetBinContent(i)*factor
            err = measured.GetBinError(i)*factor
            measured.SetBinContent(i, val)
            measured.SetBinError(i, err)

        rooresponse.Hmeasured().Add(rooresponse.Hfakes(), -1)
        rooresponse.Hfakes().Add(rooresponse.Hfakes(), -1)

    unfold = ROOT.RooUnfoldBayes(rooresponse, measured, 10)
    hReco= unfold.Hreco()
    if hReco.GetNbinsX() != measured.GetNbinsX():
        raise Exception("Different histogram sizes after unfolding")

    return hReco

def scale(h, s):
    #h.Scale(s)
    #return
    for i in xrange(0, h.GetNbinsX()+2):
        val = h.GetBinContent(i)*s
        err = h.GetBinError(i)*s
        h.SetBinContent(i, val)
        h.SetBinError(i, err)

def scale2d(h, s):
    for i in xrange(0, h.GetNbinsX()+2):
        for j in xrange(0, h.GetNbinsY()+2):
            val = h.GetBinContent(i,j)*s
            err = h.GetBinError(i, j)*s
            h.SetBinContent(i, j, val)
            h.SetBinError(i, j, err)



def getPossibleActions():
    return set(["pythiaOnData", "herwigOnData", "pythiaOnHerwig", "herwigOnPythia", "herwigOnHerwig", "pythiaOnPythia"])

def unfold(action, infileName):
    possibleActions = getPossibleActions()
    if action not in possibleActions:
        print "Action", action, "not known. Possible actions "+ " ".join(possibleActions)
        return

    categories = {}
    if action == "herwigOnData":
        baseMC = "QCD_Pt-15to1000_TuneEE3C_Flat_7TeV_herwigpp"
        categories["_jet15"] = ["Jet-Run2010B-Apr21ReReco-v1", "JetMETTau-Run2010A-Apr21ReReco-v1", "JetMET-Run2010A-Apr21ReReco-v1"]
        categories["_dj15fb"] = ["METFwd-Run2010B-Apr21ReReco-v1", "JetMETTau-Run2010A-Apr21ReReco-v1", "JetMET-Run2010A-Apr21ReReco-v1"]
    elif action == "pythiaOnData":
        baseMC = "QCD_Pt-15to3000_TuneZ2star_Flat_HFshowerLibrary_7TeV_pythia6"
        categories["_jet15"] = ["Jet-Run2010B-Apr21ReReco-v1", "JetMETTau-Run2010A-Apr21ReReco-v1", "JetMET-Run2010A-Apr21ReReco-v1"]
        categories["_dj15fb"] = ["METFwd-Run2010B-Apr21ReReco-v1", "JetMETTau-Run2010A-Apr21ReReco-v1", "JetMET-Run2010A-Apr21ReReco-v1"]
    elif action ==  "pythiaOnHerwig":
        baseMC = "QCD_Pt-15to3000_TuneZ2star_Flat_HFshowerLibrary_7TeV_pythia6"
        otherMC =  "QCD_Pt-15to1000_TuneEE3C_Flat_7TeV_herwigpp"
        categories["_jet15"] = ["QCD_Pt-15to1000_TuneEE3C_Flat_7TeV_herwigpp"]
        categories["_dj15fb"] = ["QCD_Pt-15to1000_TuneEE3C_Flat_7TeV_herwigpp"]
    elif action ==  "herwigOnPythia":
        baseMC = "QCD_Pt-15to1000_TuneEE3C_Flat_7TeV_herwigpp"
        otherMC = "QCD_Pt-15to3000_TuneZ2star_Flat_HFshowerLibrary_7TeV_pythia6"
        categories["_jet15"] = ["QCD_Pt-15to3000_TuneZ2star_Flat_HFshowerLibrary_7TeV_pythia6"]
        categories["_dj15fb"] = ["QCD_Pt-15to3000_TuneZ2star_Flat_HFshowerLibrary_7TeV_pythia6"]
    elif action ==  "herwigOnHerwig":
        baseMC = "QCD_Pt-15to1000_TuneEE3C_Flat_7TeV_herwigpp"
        otherMC =  "QCD_Pt-15to1000_TuneEE3C_Flat_7TeV_herwigpp"
        categories["_jet15"] = ["QCD_Pt-15to1000_TuneEE3C_Flat_7TeV_herwigpp"]
        categories["_dj15fb"] = ["QCD_Pt-15to1000_TuneEE3C_Flat_7TeV_herwigpp"]
    elif action ==  "pythiaOnPythia":
        baseMC = "QCD_Pt-15to3000_TuneZ2star_Flat_HFshowerLibrary_7TeV_pythia6"
        otherMC = "QCD_Pt-15to3000_TuneZ2star_Flat_HFshowerLibrary_7TeV_pythia6"
        categories["_jet15"] = ["QCD_Pt-15to3000_TuneZ2star_Flat_HFshowerLibrary_7TeV_pythia6"]
        categories["_dj15fb"] = ["QCD_Pt-15to3000_TuneZ2star_Flat_HFshowerLibrary_7TeV_pythia6"]

    


    histos = getHistos(infileName)
    #print histos.keys()
    #print histos["JetMET-Run2010A-Apr21ReReco-v1"].keys()

    knownResponses = set(filter(lambda x: x.startswith("response_"), histos[baseMC].keys()))
    #print histos[baseMC].keys()

    #responsesCentral = set(filter(lambda x: "_central_" in x, knownResponses))
    #responsesVariations = knownResponses-responsesCentral

    # _dj15fb', 
    #'response_jecDown_jet15

    of =  ROOT.TFile(odir+"/mnxsHistos_unfolded_"+action+".root","RECREATE")

    # Warning: duplicated code for lumi calculation! See mnDraw.py
    triggerToKey = {}
    triggerToKey["_jet15"] = "lumiJet15"
    triggerToKey["_dj15fb"] = "lumiDiJet15FB"

    for c in categories:
        odirROOTfile = of.mkdir(c)

        centralHistoName = "xs_central"+c # in fact we should not find any other histogram in data than "central"
        histo = None

        sampleList=CommonFSQFramework.Core.Util.getAnaDefinition("sam")
        lumi = 0.
        for ds in categories[c]:
            h = histos[ds][centralHistoName]
            if not histo:
                histo = h.Clone()
                histo.SetDirectory(0)
            else:
                histo.Add(h)

            if "Data" in action: # 
                lumiKeyName = triggerToKey[c]
                lumi += sampleList[ds][lumiKeyName]


        if "Data" in action:
            histo.Scale(1./lumi)

        print "Lumi", c, action, lumi
        rawName = "xs_central"+c

        odirROOTfile.WriteTObject(histo,rawName)
        for r in knownResponses:
            if c not in r: continue # do not apply dj15fb to jet15 and viceversa
            variation = r.split("_")[1]
            # Doing:  _dj15fb response_central_dj15fb central

            print "Doing: ", c, r, variation
            rawName = "xsunfolded_" + variation+ c
            sys.stdout.flush()

            hReco = doUnfold(histo.Clone(), histos[baseMC][r].Clone())
            hReco.SetName(rawName)
            odirROOTfile.WriteTObject(hReco, rawName)

            # http://hepunx.rl.ac.uk/~adye/software/unfold/htmldoc/src/RooUnfold.cxx.html#718
            # now - toyMC approac to limited MC statistics
            if variation == "central":
                global ntoys
                for i in xrange(0, ntoys):
                    varied = vary(hReco.Clone())
                    #print "TEST: ", hReco.Integral(), varied.Integral()
                #sys.stdout.flush()




def compareMCGentoMCUnfolded(action, infileName):
    if action == "herwigOnPythia" or action == "pythiaOnPythia":
        unfoldingWasDoneOn = "QCD_Pt-15to3000_TuneZ2star_Flat_HFshowerLibrary_7TeV_pythia6"
    elif action == "pythiaOnHerwig" or action == "herwigOnHerwig":
        unfoldingWasDoneOn = "QCD_Pt-15to1000_TuneEE3C_Flat_7TeV_herwigpp"
    else:
        print "compareMCGentoMCUnfolded: wrong action", action, "skipping (usually you can ignore this message)"
        return

    # detaGen_central_jet15
    fileWithUnfoldedPlotsName = odir+"/mnxsHistos_unfolded_"+action +".root"
    fileWithUnfoldedPlots = ROOT.TFile(fileWithUnfoldedPlotsName)


    #mnxsHistos_unfolded_pythiaOnHerwig.root
    histos = getHistos(infileName)
    #print histos[unfoldingWasDoneOn].keys()
    todo = ["_jet15", "_dj15fb"]
    #todo = ["_jet15"]

    c = ROOT.TCanvas()
    for t in todo:
        genHisto = histos[unfoldingWasDoneOn]["detaGen_central"+t]
        unfoldedHistoName = t+"/xsunfolded_central"+t
        unfoldedHisto = fileWithUnfoldedPlots.Get(unfoldedHistoName)
        #print unfoldedHistoName, type(unfoldedHisto), unfoldedHisto.ClassName()
        #genHisto.Scale(0.5)
        genHisto.Draw()
        genHisto.GetXaxis().SetTitle(DrawMNPlots.xLabels()["xs"])
        genHisto.GetYaxis().SetTitleOffset(1.8)
        genHisto.GetYaxis().SetTitle(DrawMNPlots.yLabels()["xsAsPB"])

        genHisto.SetMarkerColor(2)
        genHisto.SetLineColor(2)
        unfoldedHisto.Draw("SAME")
        trueMax = max(genHisto.GetMaximum(), unfoldedHisto.GetMaximum())
        genHisto.SetMaximum(trueMax*1.07)

        c.Print(odir+"/MConMCunfoldingTest_"+action+t+".png")

def main():
    CommonFSQFramework.Core.Style.setTDRStyle()
    possibleActions = getPossibleActions()
    global alaGri
    alaGri = True
    
    parser = OptionParser(usage="usage: %prog [options] filename",
                            version="%prog 1.0")

    parser.add_option("-v", "--variant",   action="store", dest="variant", type="string", \
                                help="choose analysis variant")



    (options, args) = parser.parse_args()
    if not options.variant:
        print "Provide analysis variant"
        sys.exit()

    infileName = "plotsMNxs_{}.root".format(options.variant)
    global odir
    odir = "~/tmp/unfolded_{}/".format(options.variant)
    os.system("mkdir -p "+odir)

    #possibleActions = ["pythiaOnPythia",  "herwigOnPythia", "pythiaOnHerwig", "herwigOnHerwig"]
    for action in possibleActions:
        unfold(action, infileName)
        compareMCGentoMCUnfolded(action, infileName)

if __name__ == "__main__":
    main()

