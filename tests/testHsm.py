#!/usr/bin/env python
# LSST Data Management System
# Copyright 2008-2015 AURA/LSST
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#

import re
import os
import sys
import glob
import math
import numpy as np
import unittest
import itertools

import lsst.pex.exceptions as pexExceptions
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import lsst.meas.base as base
import lsst.meas.algorithms as algorithms
import lsst.utils.tests as utilsTests
import lsst.afw.detection as afwDetection
import lsst.afw.table as afwTable
import lsst.afw.geom as afwGeom
import lsst.afw.geom.ellipses as afwEll
import lsst.afw.coord as afwCoord
import lsst.afw.display.ds9 as ds9

import lsst.meas.extensions.shapeHSM

try:
    type(verbose)
except NameError:
    verbose = 0
    display = False

SIZE_DECIMALS = 2  # Number of decimals for equality in sizes
SHAPE_DECIMALS = 3  # Number of decimals for equality in shapes

# The following values are pulled directly from GalSim's test_hsm.py:
file_indices = [0, 2, 4, 6, 8]
x_centroid = [35.888, 19.44, 8.74, 20.193, 57.94]
y_centroid = [19.845, 25.047, 11.92, 38.93, 27.73]
sky_var = [35.01188, 35.93418, 35.15456, 35.11146, 35.16454]
correction_methods = ["KSB", "BJ", "LINEAR", "REGAUSS"]
# Note: expected results give shear for KSB and distortion for others, but the results below have
# converted KSB expected results to distortion for the sake of consistency
e1_expected = np.array([
    [0.467603106752, 0.381211727, 0.398856937, 0.401755571],
    [0.28618443944, 0.199222784, 0.233883543, 0.234257525],
    [0.271533794146, 0.158049396, 0.183517068, 0.184893412],
    [-0.293754156071, -0.457024541, 0.123946584, -0.609233462],
    [0.557720893779, 0.374143023, 0.714147448, 0.435404409]])
e2_expected = np.array([
    [-0.867225166489, -0.734855778, -0.777027588, -0.774684891],
    [-0.469354341577, -0.395520479, -0.502540961, -0.464466257],
    [-0.519775291311, -0.471589061, -0.574750641, -0.529664935],
    [0.345688365839, -0.342047099, 0.120603755, -0.44609129428863525],
    [0.525728304099, 0.370691830, 0.702724807, 0.433999442]])
resolution_expected = np.array([
    [0.796144249, 0.835624917, 0.835624917, 0.827796187],
    [0.685023735, 0.699602704, 0.699602704, 0.659457638],
    [0.634736458, 0.651040481, 0.651040481, 0.614663396],
    [0.477027015, 0.477210752, 0.477210752, 0.423157447],
    [0.595205998, 0.611824797, 0.611824797, 0.563582092]])
sigma_e_expected = np.array([
    [0.016924826, 0.014637648, 0.014637648, 0.014465546],
    [0.075769504, 0.073602324, 0.073602324, 0.064414520],
    [0.110253112, 0.106222900, 0.106222900, 0.099357106],
    [0.185276702, 0.184300955, 0.184300955, 0.173478300],
    [0.073020065, 0.070270966, 0.070270966, 0.061856263]])
# End of GalSim's values

# These values calculated using GalSim's HSM as part of GalSim
galsim_e1 = np.array([
    [0.399292618036, 0.381213068962, 0.398856908083, 0.401749581099],
    [0.155929282308, 0.199228107929, 0.233882278204, 0.234371587634],
    [0.150018423796, 0.158052951097, 0.183515056968, 0.184561833739],
    [-2.6984937191, -0.457033962011, 0.123932465911, -0.60886412859],
    [0.33959621191, 0.374140143394, 0.713756918907, 0.43560180068],
])
galsim_e2 = np.array([
    [-0.74053555727, -0.734855830669, -0.777024209499, -0.774700462818],
    [-0.25573053956, -0.395517915487, -0.50251352787, -0.464388132095],
    [-0.287168383598, -0.471584022045, -0.574719130993, -0.5296921134],
    [3.1754450798, -0.342054128647, 0.120592080057, -0.446093201637],
    [0.320115834475, 0.370669454336, 0.702303349972, 0.433968126774],
])
galsim_resolution = np.array([
    [0.79614430666, 0.835625052452, 0.835625052452, 0.827822327614],
    [0.685023903847, 0.699601829052, 0.699601829052, 0.659438848495],
    [0.634736537933, 0.651039719582, 0.651039719582, 0.614759743214],
    [0.477026551962, 0.47721144557, 0.47721144557, 0.423227936029],
    [0.595205545425, 0.611821532249, 0.611821532249, 0.563564240932],
])
galsim_err = np.array([
    [0.0169247947633, 0.0146376201883, 0.0146376201883, 0.0144661813974],
    [0.0757696777582, 0.0736026018858, 0.0736026018858, 0.0644160583615],
    [0.110252402723, 0.106222368777, 0.106222368777, 0.0993555411696],
    [0.185278102756, 0.184301897883, 0.184301897883, 0.17346136272],
    [0.0730196461082, 0.0702708885074, 0.0702708885074, 0.0618583671749],
])

moments_expected = np.array([  # sigma, e1, e2
    [2.24490427971, 0.336240686301, -0.627372910656],
    [1.9031778574, 0.150566105384, -0.245272792302],
    [1.77790760994, 0.112286123389, -0.286203939641],
    [1.45464873314, -0.155597168978, -0.102008266223],
    [1.63144648075, 0.22886961923, 0.228813588897],
])
centroid_expected = np.array([  # x, y
    [36.218247328, 20.5678722157],
    [20.325744838, 25.4176650386],
    [9.54257706283, 12.6134786199],
    [20.6407850048, 39.5864802706],
    [58.5008586442, 28.2850942049],
])


def makePluginAndCat(alg, name, control=None, metadata=False, centroid=None):
    print "Making plugin ", alg, name
    if control == None:
        control = alg.ConfigClass()
    schema = afwTable.SourceTable.makeMinimalSchema()
    if centroid:
        schema.addField(centroid + "_x", type=float)
        schema.addField(centroid + "_y", type=float)
        schema.addField(centroid + "_flag", type='Flag')
        schema.getAliasMap().set("slot_Centroid", centroid)
    if metadata:
        plugin = alg(control, name, schema, dafBase.PropertySet())
    else:
        plugin = alg(control, name, schema)
    cat = afwTable.SourceCatalog(schema)
    if centroid:
        cat.defineCentroid(centroid)
    return plugin, cat

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-


class ShapeTestCase(unittest.TestCase):
    """A test case for shape measurement"""

    def setUp(self):

        # load the known values
        self.dataDir = os.path.join(os.getenv('MEAS_EXTENSIONS_SHAPEHSM_DIR'), "tests", "data")
        self.bkgd = 1000.0  # standard for atlas image
        self.offset = afwGeom.Extent2I(1234, 1234)
        self.xy0 = afwGeom.Point2I(5678, 9876)

    def tearDown(self):
        del self.offset
        del self.xy0

    def runMeasurement(self, algorithmName, imageid, x, y, v):
        """Run the measurement algorithm on an image"""
        # load the test image
        imgFile = os.path.join(self.dataDir, "image.%d.fits" % imageid)
        img = afwImage.ImageF(imgFile)
        img -= self.bkgd
        nx, ny = img.getWidth(), img.getHeight()
        msk = afwImage.MaskU(afwGeom.Extent2I(nx, ny), 0x0)
        var = afwImage.ImageF(afwGeom.Extent2I(nx, ny), v)
        mimg = afwImage.MaskedImageF(img, msk, var)
        msk.getArray()[:] = np.where(np.fabs(img.getArray()) < 1.0e-8, msk.getPlaneBitMask("BAD"), 0)

        # Put it in a bigger image, in case it matters
        big = afwImage.MaskedImageF(self.offset + mimg.getDimensions())
        big.getImage().set(0)
        big.getMask().set(0)
        big.getVariance().set(v)
        subBig = afwImage.MaskedImageF(big, afwGeom.Box2I(big.getXY0() + self.offset, mimg.getDimensions()))
        subBig <<= mimg
        mimg = big
        mimg.setXY0(self.xy0)

        exposure = afwImage.makeExposure(mimg)
        exposure.setWcs(afwImage.makeWcs(afwCoord.makeCoord(afwCoord.ICRS, 0. * afwGeom.degrees, 0. * afwGeom.degrees),
                                         afwGeom.Point2D(1.0, 1.0),
                                         1.0/(2.53*3600.0), 0.0, 0.0, 1.0/(2.53*3600.0)))

        # load the corresponding test psf
        psfFile = os.path.join(self.dataDir, "psf.%d.fits" % imageid)
        psfImg = afwImage.ImageD(psfFile)
        psfImg -= self.bkgd

        kernel = afwMath.FixedKernel(psfImg)
        kernelPsf = algorithms.KernelPsf(kernel)
        exposure.setPsf(kernelPsf)

        # perform the shape measurement
        msConfig = base.SingleFrameMeasurementConfig()
        alg = base.SingleFramePlugin.registry[algorithmName].PluginClass.AlgClass
        control = base.SingleFramePlugin.registry[algorithmName].PluginClass.ConfigClass().makeControl()
        msConfig.algorithms.names = [algorithmName]
        # Note: It is essential to remove the floating point part of the position for the
        # Algorithm._apply.  Otherwise, when the PSF is realised it will have been warped
        # to account for the sub-pixel offset and we won't get *exactly* this PSF.
        plugin, table = makePluginAndCat(alg, algorithmName, control, centroid="centroid")
        center = afwGeom.Point2D(int(x), int(y)) + afwGeom.Extent2D(self.offset + afwGeom.Extent2I(self.xy0))
        source = table.makeRecord()
        source.set("centroid_x", center.getX())
        source.set("centroid_y", center.getY())
        source.setFootprint(afwDetection.Footprint(exposure.getBBox(afwImage.PARENT)))
        plugin.measure(source, exposure)

        return source

    def testHsmShape(self):
        """Test that we can instantiate and play with a measureShape"""

        nFail = 0
        msg = ""

        for (algNum, algName), (i, imageid) in itertools.product(enumerate(correction_methods),
                                                                 enumerate(file_indices)):
            algorithmName = "ext_shapeHSM_HsmShape" + algName[0:1].upper() + algName[1:].lower()

            source = self.runMeasurement(algorithmName, imageid, x_centroid[i], y_centroid[i], sky_var[i])

            ##########################################
            # see how we did
            if algName in ("KSB"):
                # Need to convert g1,g2 --> e1,e2 because GalSim has done that
                # for the expected values ("for consistency")
                g1 = source.get(algorithmName + "_g1")
                g2 = source.get(algorithmName + "_g2")
                scale = 2.0/(1.0 + g1**2 + g2**2)
                e1 = g1*scale
                e2 = g2*scale
                sigma = source.get(algorithmName + "_sigma")
            else:
                e1 = source.get(algorithmName + "_e1")
                e2 = source.get(algorithmName + "_e2")
                sigma = 0.5*source.get(algorithmName + "_sigma")
            resolution = source.get(algorithmName + "_resolution")
            flags = source.get(algorithmName + "_flag")

            tests = [
                # label        known-value                            measured              tolerance
                ["e1", float(e1_expected[i][algNum]), e1, 0.5*10**-SHAPE_DECIMALS],
                ["e2", float(e2_expected[i][algNum]), e2, 0.5*10**-SHAPE_DECIMALS],
                ["resolution", float(resolution_expected[i][algNum]), resolution, 0.5*10**-SIZE_DECIMALS],

                # sigma won't match exactly because
                # we're using skyvar=mean(var) instead of measured value ... expected a difference
                ["sigma", float(sigma_e_expected[i][algNum]), sigma, 0.07],
                ["shapeStatus", 0, flags, 0],
            ]

            for test in tests:
                label, know, hsm, limit = test
                err = hsm - know
                msgTmp = "%-12s %s  %5s:   %6.6f %6.6f  (val-known) = %.3g\n" % (algName, imageid,
                                                                                 label, know, hsm, err)
                if not np.isfinite(err) or abs(err) > limit:
                    msg += msgTmp
                    nFail += 1

            self.assertAlmostEqual(g1 if algName in ("KSB") else e1, galsim_e1[i][algNum], SHAPE_DECIMALS)
            self.assertAlmostEqual(g2 if algName in ("KSB") else e2, galsim_e2[i][algNum], SHAPE_DECIMALS)
            self.assertAlmostEqual(resolution, galsim_resolution[i][algNum], SIZE_DECIMALS)
            self.assertAlmostEqual(sigma, galsim_err[i][algNum], delta=0.07)

        self.assertEqual(nFail, 0, "\n"+msg)

    def testHsmSourceMoments(self):
        for (i, imageid) in enumerate(file_indices):
            source = self.runMeasurement("ext_shapeHSM_HsmSourceMoments", imageid, x_centroid[i], y_centroid[i],
                                         sky_var[i])
            x = source.get("ext_shapeHSM_HsmSourceMoments_x")
            y = source.get("ext_shapeHSM_HsmSourceMoments_y")
            xx = source.get("ext_shapeHSM_HsmSourceMoments_xx")
            yy = source.get("ext_shapeHSM_HsmSourceMoments_yy")
            xy = source.get("ext_shapeHSM_HsmSourceMoments_xy")

            # Centroids from GalSim use the FITS lower-left corner of 1,1
            offset = self.xy0 + self.offset
            self.assertAlmostEqual(x - offset.getX(), centroid_expected[i][0] - 1, 3)
            self.assertAlmostEqual(y - offset.getY(), centroid_expected[i][1] - 1, 3)

            expected = afwEll.Quadrupole(afwEll.SeparableDistortionDeterminantRadius(
                moments_expected[i][1], moments_expected[i][2], moments_expected[i][0]))

            self.assertAlmostEqual(xx, expected.getIxx(), SHAPE_DECIMALS)
            self.assertAlmostEqual(xy, expected.getIxy(), SHAPE_DECIMALS)
            self.assertAlmostEqual(yy, expected.getIyy(), SHAPE_DECIMALS)

    def testHsmPsfMoments(self):
        for width in (2.0, 3.0, 4.0):
            psf = afwDetection.GaussianPsf(35, 35, width)
            exposure = afwImage.ExposureF(45, 56)
            exposure.getMaskedImage().set(1.0, 0, 1.0)
            exposure.setPsf(psf)

            # perform the shape measurement
            msConfig = base.SingleFrameMeasurementConfig()
            msConfig.algorithms.names = ["ext_shapeHSM_HsmPsfMoments"]
            plugin, cat = makePluginAndCat(lsst.meas.extensions.shapeHSM.HsmPsfMomentsAlgorithm,
                                           "ext_shapeHSM_HsmPsfMoments", centroid="centroid",
                                           control=lsst.meas.extensions.shapeHSM.HsmPsfMomentsControl())
            source = cat.addNew()
            source.set("centroid_x", 23)
            source.set("centroid_y", 34)
            source.setFootprint(afwDetection.Footprint(afwGeom.Point2I(23, 34), width))
            plugin.measure(source, exposure)
            x = source.get("ext_shapeHSM_HsmPsfMoments_x")
            y = source.get("ext_shapeHSM_HsmPsfMoments_y")
            xx = source.get("ext_shapeHSM_HsmPsfMoments_xx")
            yy = source.get("ext_shapeHSM_HsmPsfMoments_yy")
            xy = source.get("ext_shapeHSM_HsmPsfMoments_xy")

            self.assertAlmostEqual(x, 0.0, 3)
            self.assertAlmostEqual(y, 0.0, 3)

            expected = afwEll.Quadrupole(afwEll.Axes(width, width, 0.0))

            self.assertAlmostEqual(xx, expected.getIxx(), SHAPE_DECIMALS)
            self.assertAlmostEqual(xy, expected.getIxy(), SHAPE_DECIMALS)
            self.assertAlmostEqual(yy, expected.getIyy(), SHAPE_DECIMALS)

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-


def suite():
    """Returns a suite containing all the test cases in this module."""
    utilsTests.init()

    suites = []
    suites += unittest.makeSuite(ShapeTestCase)
    suites += unittest.makeSuite(utilsTests.MemoryTestCase)

    return unittest.TestSuite(suites)


def run(exit = False):
    """Run the tests"""
    utilsTests.run(suite(), exit)

if __name__ == "__main__":
    run(True)
