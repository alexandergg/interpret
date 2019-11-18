# Copyright (c) 2019 Microsoft Corporation
# Distributed under the MIT software license

# TODO: Add unit tests for internal EBM interfacing
import sys
from sys import platform
import ctypes as ct
from numpy.ctypeslib import ndpointer
import numpy as np
import os
import struct
import logging
from contextlib import closing

from .utils import EBMUtils

log = logging.getLogger(__name__)

class Native:
    """Layer/Class responsible for native function calls."""
    
    _native = None

    def _initialize(self, is_debug, log_level):
        self.is_debug = is_debug
        self.log_level = log_level

        self.lib = ct.cdll.LoadLibrary(Native._get_ebm_lib_path(debug=is_debug))
        self._harden_function_signatures()
        self._set_logging(level=log_level)

    @staticmethod
    def get_native_singleton(is_debug=False, log_level=None):
        log.debug("Check if EBM lib is loaded")
        if Native._native is None:
            log.info("EBM lib loading.")
            native = Native()
            native._initialize(is_debug=is_debug, log_level=log_level)
            Native._native = native
        else:
            log.debug("EBM lib already loaded")
        return Native._native

    # enum FeatureType : int64_t
    # Ordinal = 0
    FeatureTypeOrdinal = 0
    # Nominal = 1
    FeatureTypeNominal = 1

    class EbmCoreFeature(ct.Structure):
        _fields_ = [
            # FeatureType featureType;
            ("featureType", ct.c_longlong),
            # bool hasMissing;
            ("hasMissing", ct.c_longlong),
            # int64_t countBins;
            ("countBins", ct.c_longlong),
        ]

    class EbmCoreFeatureCombination(ct.Structure):
        _fields_ = [
            # int64_t countFeaturesInCombination;
            ("countFeaturesInCombination", ct.c_longlong)
        ]

    # const signed char TraceLevelOff = 0;
    TraceLevelOff = 0
    # const signed char TraceLevelError = 1;
    TraceLevelError = 1
    # const signed char TraceLevelWarning = 2;
    TraceLevelWarning = 2
    # const signed char TraceLevelInfo = 3;
    TraceLevelInfo = 3
    # const signed char TraceLevelVerbose = 4;
    TraceLevelVerbose = 4

    _LogFuncType = ct.CFUNCTYPE(None, ct.c_char, ct.c_char_p)

    def __init__(self):
        pass

    def _harden_function_signatures(self):
        """ Adds types to function signatures. """
        self.lib.SetLogMessageFunction.argtypes = [
            # void (* fn)(signed char traceLevel, const char * message) logMessageFunction
            self._LogFuncType
        ]
        self.lib.SetTraceLevel.argtypes = [
            # signed char traceLevel
            ct.c_char
        ]

        self.lib.InitializeTrainingClassification.argtypes = [
            # int64_t countTargetClasses
            ct.c_longlong,
            # int64_t countFeatures
            ct.c_longlong,
            # EbmCoreFeature * features
            ct.POINTER(self.EbmCoreFeature),
            # int64_t countFeatureCombinations
            ct.c_longlong,
            # EbmCoreFeatureCombination * featureCombinations
            ct.POINTER(self.EbmCoreFeatureCombination),
            # int64_t * featureCombinationIndexes
            ndpointer(dtype=np.int64, ndim=1),
            # int64_t countTrainingInstances
            ct.c_longlong,
            # int64_t * trainingBinnedData
            ndpointer(dtype=np.int64, ndim=2, flags="C_CONTIGUOUS"),
            # int64_t * trainingTargets
            ndpointer(dtype=np.int64, ndim=1),
            # double * trainingPredictorScores
            # scores can either be 1 or 2 dimensional
            ndpointer(dtype=np.float64, flags="C_CONTIGUOUS"),
            # int64_t countValidationInstances
            ct.c_longlong,
            # int64_t * validationBinnedData
            ndpointer(dtype=np.int64, ndim=2, flags="C_CONTIGUOUS"),
            # int64_t * validationTargets
            ndpointer(dtype=np.int64, ndim=1),
            # double * validationPredictorScores
            # scores can either be 1 or 2 dimensional
            ndpointer(dtype=np.float64, flags="C_CONTIGUOUS"),
            # int64_t countInnerBags
            ct.c_longlong,
            # int64_t randomSeed
            ct.c_longlong
        ]
        self.lib.InitializeTrainingClassification.restype = ct.c_void_p

        self.lib.InitializeTrainingRegression.argtypes = [
            # int64_t countFeatures
            ct.c_longlong,
            # EbmCoreFeature * features
            ct.POINTER(self.EbmCoreFeature),
            # int64_t countFeatureCombinations
            ct.c_longlong,
            # EbmCoreFeatureCombination * featureCombinations
            ct.POINTER(self.EbmCoreFeatureCombination),
            # int64_t * featureCombinationIndexes
            ndpointer(dtype=np.int64, ndim=1),
            # int64_t countTrainingInstances
            ct.c_longlong,
            # int64_t * trainingBinnedData
            ndpointer(dtype=np.int64, ndim=2, flags="C_CONTIGUOUS"),
            # double * trainingTargets
            ndpointer(dtype=np.float64, ndim=1),
            # double * trainingPredictorScores
            ndpointer(dtype=np.float64, ndim=1),
            # int64_t countValidationInstances
            ct.c_longlong,
            # int64_t * validationBinnedData
            ndpointer(dtype=np.int64, ndim=2, flags="C_CONTIGUOUS"),
            # double * validationTargets
            ndpointer(dtype=np.float64, ndim=1),
            # double * validationPredictorScores
            ndpointer(dtype=np.float64, ndim=1),
            # int64_t countInnerBags
            ct.c_longlong,
            # int64_t randomSeed
            ct.c_longlong
        ]
        self.lib.InitializeTrainingRegression.restype = ct.c_void_p

        self.lib.GenerateModelFeatureCombinationUpdate.argtypes = [
            # void * ebmTraining
            ct.c_void_p,
            # int64_t indexFeatureCombination
            ct.c_longlong,
            # double learningRate
            ct.c_double,
            # int64_t countTreeSplitsMax
            ct.c_longlong,
            # int64_t countInstancesRequiredForParentSplitMin
            ct.c_longlong,
            # double * trainingWeights
            # ndpointer(dtype=np.float64, ndim=1),
            ct.c_void_p,
            # double * validationWeights
            # ndpointer(dtype=np.float64, ndim=1),
            ct.c_void_p,
            # double * gainReturn
            ct.POINTER(ct.c_double),
        ]
        self.lib.GenerateModelFeatureCombinationUpdate.restype = ct.POINTER(ct.c_double)

        self.lib.ApplyModelFeatureCombinationUpdate.argtypes = [
            # void * ebmTraining
            ct.c_void_p,
            # int64_t indexFeatureCombination
            ct.c_longlong,
            # double * modelFeatureCombinationUpdateTensor
            ct.POINTER(ct.c_double),
            # double * validationMetricReturn
            ct.POINTER(ct.c_double),
        ]
        self.lib.ApplyModelFeatureCombinationUpdate.restype = ct.c_longlong

        self.lib.GetBestModelFeatureCombination.argtypes = [
            # void * ebmTraining
            ct.c_void_p,
            # int64_t indexFeatureCombination
            ct.c_longlong,
        ]
        self.lib.GetBestModelFeatureCombination.restype = ct.POINTER(ct.c_double)

        self.lib.GetCurrentModelFeatureCombination.argtypes = [
            # void * ebmTraining
            ct.c_void_p,
            # int64_t indexFeatureCombination
            ct.c_longlong,
        ]
        self.lib.GetCurrentModelFeatureCombination.restype = ct.POINTER(ct.c_double)

        self.lib.FreeTraining.argtypes = [
            # void * ebmTraining
            ct.c_void_p
        ]

        self.lib.InitializeInteractionClassification.argtypes = [
            # int64_t countTargetClasses
            ct.c_longlong,
            # int64_t countFeatures
            ct.c_longlong,
            # EbmCoreFeature * features
            ct.POINTER(self.EbmCoreFeature),
            # int64_t countInstances
            ct.c_longlong,
            # int64_t * binnedData
            ndpointer(dtype=np.int64, ndim=2, flags="C_CONTIGUOUS"),
            # int64_t * targets
            ndpointer(dtype=np.int64, ndim=1),
            # double * predictorScores
            # scores can either be 1 or 2 dimensional
            ndpointer(dtype=np.float64, flags="C_CONTIGUOUS"),
        ]
        self.lib.InitializeInteractionClassification.restype = ct.c_void_p

        self.lib.InitializeInteractionRegression.argtypes = [
            # int64_t countFeatures
            ct.c_longlong,
            # EbmCoreFeature * features
            ct.POINTER(self.EbmCoreFeature),
            # int64_t countInstances
            ct.c_longlong,
            # int64_t * binnedData
            ndpointer(dtype=np.int64, ndim=2, flags="C_CONTIGUOUS"),
            # double * targets
            ndpointer(dtype=np.float64, ndim=1),
            # double * predictorScores
            ndpointer(dtype=np.float64, ndim=1),
        ]
        self.lib.InitializeInteractionRegression.restype = ct.c_void_p

        self.lib.GetInteractionScore.argtypes = [
            # void * ebmInteraction
            ct.c_void_p,
            # int64_t countFeaturesInCombination
            ct.c_longlong,
            # int64_t * featureIndexes
            ndpointer(dtype=np.int64, ndim=1),
            # double * interactionScoreReturn
            ct.POINTER(ct.c_double),
        ]
        self.lib.GetInteractionScore.restype = ct.c_longlong

        self.lib.FreeInteraction.argtypes = [
            # void * ebmInteraction
            ct.c_void_p
        ]

    def _set_logging(self, level=None):
        def native_log(trace_level, message):
            try:
                trace_level = int(trace_level[0])
                message = message.decode("ascii")

                if trace_level == self.TraceLevelError:
                    log.error(message)
                elif trace_level == self.TraceLevelWarning:
                    log.warning(message)
                elif trace_level == self.TraceLevelInfo:
                    log.info(message)
                elif trace_level == self.TraceLevelVerbose:
                    log.debug(message)
            except: # we're being called from C, so we can't raise exceptions
                pass

        if level is None:
            root = logging.getLogger("interpret")
            level = root.getEffectiveLevel()

        level_dict = {
            logging.DEBUG: self.TraceLevelVerbose,
            logging.INFO: self.TraceLevelInfo,
            logging.WARNING: self.TraceLevelWarning,
            logging.ERROR: self.TraceLevelError,
            logging.CRITICAL: self.TraceLevelError,
            logging.NOTSET: self.TraceLevelOff,
            "DEBUG": self.TraceLevelVerbose,
            "INFO": self.TraceLevelInfo,
            "WARNING": self.TraceLevelWarning,
            "ERROR": self.TraceLevelError,
            "CRITICAL": self.TraceLevelError,
            "NOTSET": self.TraceLevelOff,
        }

        # it's critical that we put typed_log_func into self, 
        # otherwise it will be garbage collected
        self.typed_log_func = self._LogFuncType(native_log)
        
        self.lib.SetLogMessageFunction(self.typed_log_func)
        self.lib.SetTraceLevel(ct.c_char(level_dict[level]))

    @staticmethod
    def _get_ebm_lib_path(debug=False):
        """ Returns filepath of core EBM library.

        Returns:
            A string representing filepath.
        """
        bitsize = struct.calcsize("P") * 8
        is_64_bit = bitsize == 64

        script_path = os.path.dirname(os.path.abspath(__file__))
        package_path = os.path.join(script_path, "..", "..")

        debug_str = "_debug" if debug else ""
        log.info("Loading native on {0} | debug = {1}".format(platform, debug))
        if platform == "linux" or platform == "linux2" and is_64_bit:
            return os.path.join(
                package_path, "lib", "lib_ebmcore_linux_x64{0}.so".format(debug_str)
            )
        elif platform == "win32" and is_64_bit:
            return os.path.join(
                package_path, "lib", "lib_ebmcore_win_x64{0}.dll".format(debug_str)
            )
        elif platform == "darwin" and is_64_bit:
            return os.path.join(
                package_path, "lib", "lib_ebmcore_mac_x64{0}.dylib".format(debug_str)
            )
        else:
            msg = "Platform {0} at {1} bit not supported for EBM".format(
                platform, bitsize
            )
            log.error(msg)
            raise Exception(msg)

    @staticmethod
    def make_ndarray(c_pointer, shape, dtype, writable=False, copy_data=True):
        """ Returns an ndarray based from a C array.

        Code largely borrowed from:
        https://stackoverflow.com/questions/4355524/getting-data-from-ctypes-array-into-numpy

        Args:
            c_pointer: Pointer to C array.
            shape: Shape of ndarray to form.
            dtype: Numpy data type.

        Returns:
            An ndarray.
        """

        arr_size = np.prod(shape[:]) * np.dtype(dtype).itemsize
        buf_from_mem = ct.pythonapi.PyMemoryView_FromMemory
        buf_from_mem.restype = ct.py_object
        buf_from_mem.argtypes = (ct.c_void_p, ct.c_ssize_t, ct.c_int)
        PyBUF_READ = 0x100
        PyBUF_WRITE = 0x200
        access = (PyBUF_READ | PyBUF_WRITE) if writable else PyBUF_READ
        buffer = buf_from_mem(c_pointer, arr_size, access)
        # from https://github.com/python/cpython/blob/master/Objects/memoryobject.c , PyMemoryView_FromMemory can return null
        if not buffer:
            raise MemoryError("Out of memory in PyMemoryView_FromMemory")
        arr = np.ndarray(tuple(shape[:]), dtype, buffer, order="C")
        if copy_data:
            return arr.copy()
        else:
            return arr

    @staticmethod
    def convert_features_to_c(features):
        # Create C form of features

        feature_ar = (Native.EbmCoreFeature * len(features))()
        for idx, feature in enumerate(features):
            if feature["type"] == "categorical":
                feature_ar[idx].featureType = Native.FeatureTypeNominal
            elif feature["type"] == "continuous":
                feature_ar[idx].featureType = Native.FeatureTypeOrdinal
            else:
                raise AttributeError("Unrecognized feature[\"type\"]")
            feature_ar[idx].hasMissing = 1 * feature["has_missing"]
            feature_ar[idx].countBins = feature["n_bins"]

        return feature_ar

    @staticmethod
    def convert_feature_combinations_to_c(feature_combinations):
        # Create C form of feature_combinations

        feature_combination_indexes = []
        feature_combinations_ar = (
            Native.EbmCoreFeatureCombination * len(feature_combinations)
        )()
        for idx, feature_combination in enumerate(feature_combinations):
            features_in_combination = feature_combination["attributes"]
            feature_combinations_ar[idx].countFeaturesInCombination = len(features_in_combination)

            for feature_idx in features_in_combination:
                feature_combination_indexes.append(feature_idx)

        feature_combination_indexes = np.array(feature_combination_indexes, dtype=ct.c_longlong)

        return feature_combinations_ar, feature_combination_indexes


class NativeEBMTraining:
    """Lightweight wrapper for EBM C training code.
    """

    def __init__(
        self,
        model_type,
        n_classes,
        features,
        feature_combinations,
        X_train,
        y_train,
        scores_train,
        X_val,
        y_val,
        scores_val,
        n_inner_bags,
        random_state
    ):

        """ Initializes internal wrapper for EBM C code.

        Args:
            model_type: 'regression'/'classification'.
            n_classes: Specific to classification,
                number of unique classes.
            features: List of features represented individually as
                dictionary of keys ('type', 'has_missing', 'n_bins').
            feature_combinations: List of feature combinations represented as
                a dictionary of keys ("features")
            X_train: Training design matrix as 2-D ndarray.
            y_train: Training response as 1-D ndarray.
            scores_train: training predictions from a prior predictor
                that this class will boost on top of.  For regression
                there is 1 prediction per instance.  For binary classification
                there is one logit.  For multiclass there are n_classes logits
            X_val: Validation design matrix as 2-D ndarray.
            y_val: Validation response as 1-D ndarray.
            scores_val: Validation predictions from a prior predictor
                that this class will boost on top of.  For regression
                there is 1 prediction per instance.  For binary classification
                there is one logit.  For multiclass there are n_classes logits
            n_inner_bags: number of inner bags.
            random_state: Random seed as integer.
        """

        # first set the one thing that we will close on
        self._model_pointer = None

        self._native = Native.get_native_singleton()

        log.info("Allocation training start")

        # Store args
        self._model_type = model_type
        self._n_classes = n_classes

        self._features = features
        feature_array = Native.convert_features_to_c(features)

        self._feature_combinations = feature_combinations
        feature_combinations_array, feature_combination_indexes = Native.convert_feature_combinations_to_c(
            feature_combinations
        )

        if scores_train is None:
            n_scores = EBMUtils.get_count_scores_c(n_classes)
            scores_train = np.zeros(len(y_train) * n_scores, dtype=np.float64, order='C')
        if scores_val is None:
            n_scores = EBMUtils.get_count_scores_c(n_classes)
            scores_val = np.zeros(len(y_val) * n_scores, dtype=np.float64, order='C')

        # Allocate external resources
        if model_type == "classification":
            self._model_pointer = self._native.lib.InitializeTrainingClassification(
                n_classes,
                len(feature_array),
                feature_array,
                len(feature_combinations_array),
                feature_combinations_array,
                feature_combination_indexes,
                len(y_train),
                X_train,
                y_train,
                scores_train,
                len(y_val),
                X_val,
                y_val,
                scores_val,
                n_inner_bags,
                random_state
            )
            if not self._model_pointer:  # pragma: no cover
                raise MemoryError("Out of memory in InitializeTrainingClassification")
        elif model_type == "regression":
            self._model_pointer = self._native.lib.InitializeTrainingRegression(
                len(feature_array),
                feature_array,
                len(feature_combinations_array),
                feature_combinations_array,
                feature_combination_indexes,
                len(y_train),
                X_train,
                y_train,
                scores_train,
                len(y_val),
                X_val,
                y_val,
                scores_val,
                n_inner_bags,
                random_state
            )
            if not self._model_pointer:  # pragma: no cover
                raise MemoryError("Out of memory in InitializeTrainingRegression")
        else:
            raise AttributeError("Unrecognized model_type")

        log.info("Allocation training end")

    def close(self):
        """ Deallocates C objects used to train EBM. """
        log.info("Deallocation training start")
        self._native.lib.FreeTraining(self._model_pointer)
        log.info("Deallocation training end")

    def training_step(
        self,
        feature_combination_index,
        learning_rate,
        max_tree_splits,
        min_cases_for_split,
        training_step_episodes,
    ):

        """ Conducts a training step per feature
            by growing a shallow decision tree.

        Args:
            feature_combination_index: The index for the feature combination
                to train on.
            learning_rate: Learning rate as a float.
            max_tree_splits: Max tree splits on feature step.
            min_cases_for_split: Min observations required to split.
            training_step_episodes: Number of episodes to train feature step.

        Returns:
            Validation loss for the training step.
        """
        # log.debug("Training step start")

        metric_output = ct.c_double(0.0)
        # for a classification problem with only 1 target value, we will always predict the answer perfectly
        if self._model_type != "classification" or 2 <= self._n_classes:
            gain = ct.c_double(0.0)
            for i in range(training_step_episodes):
                model_update_tensor_pointer = self._native.lib.GenerateModelFeatureCombinationUpdate(
                    self._model_pointer,
                    feature_combination_index,
                    learning_rate,
                    max_tree_splits,
                    min_cases_for_split,
                    0,
                    0,
                    ct.byref(gain),
                )
                if not model_update_tensor_pointer:  # pragma: no cover
                    raise MemoryError("Out of memory in GenerateModelFeatureCombinationUpdate")

                # TODO PK convert model_update_tensor_pointer into a view (verify that we aren't copying the data) before
                #         passing it into ApplyModelFeatureCombinationUpdate (which we need to change to accept a view)
                #         This will make it more useable in python for experimentation and if we aren't copying
                #         it then performance won't be impacted at all

                return_code = self._native.lib.ApplyModelFeatureCombinationUpdate(
                    self._model_pointer,
                    feature_combination_index,
                    model_update_tensor_pointer,
                    ct.byref(metric_output),
                )
                if return_code != 0:  # pragma: no cover
                    raise Exception("Out of memory in ApplyModelFeatureCombinationUpdate")

        # log.debug("Training step end")
        return metric_output.value

    def _get_feature_combination_shape(self, feature_combination_index):
        # Retrieve dimensions of log odds tensor
        dimensions = []
        feature_combination = self._feature_combinations[feature_combination_index]
        for _, feature_idx in enumerate(feature_combination["attributes"]):
            n_bins = self._features[feature_idx]["n_bins"]
            dimensions.append(n_bins)

        dimensions = list(reversed(dimensions))

        # Array returned for multiclass is one higher dimension
        if self._model_type == "classification" and self._n_classes > 2:
            dimensions.append(self._n_classes)

        shape = tuple(dimensions)
        return shape

    def _get_best_model_feature_combination(self, feature_combination_index):
        """ Returns best model/function according to validation set
            for a given feature combination.

        Args:
            feature_combination_index: The index for the feature combination.

        Returns:
            An ndarray that represents the model.
        """

        if self._model_type == "classification" and self._n_classes <= 1:
            # if there is only one legal state for a classification problem, then we know with 100%
            # certainty what the result will be, and our logits for that result should be infinity
            # since we reduce the number of logits by 1, we would get back an empty array from the C code
            # after we expand the model for our caller, the tensor's dimensions should match
            # the features for the feature_combination, but the last class_index should have a dimension
            # of 1 for the infinities.  This all needs to be special cased anyways, so we can just return
            # a None value here for now and handle in the upper levels
            #
            # If we were to allow datasets with zero instances, then it would also be legal for there
            # to be 0 states.  We can probably handle this the same as having 1 state though since 
            # any instances in any evaluations need to have a state

            # TODO PK make sure the None value here is handled by our caller
            return None

        # TODO PK v.2 currently we return only a single logit for binary classification
        #             for the positive case (the one with target 1).  scikit also 
        #             stores and returns 1 logit, but they say to do softmax, make the
        #             target0 logit equal to the negative of the target1 logit.
        #             this has the nice property that it would closely match what you'd
        #             see in a multiclass problem with very few cases other than the 0th and 1th
        #             cases.  Do we want to do the same for conformance and in graphing

        array_p = self._native.lib.GetBestModelFeatureCombination(
            self._model_pointer, feature_combination_index
        )

        if not array_p:  # pragma: no cover
            raise MemoryError("Out of memory in GetBestModelFeatureCombination")

        shape = self._get_feature_combination_shape(feature_combination_index)

        array = Native.make_ndarray(array_p, shape, dtype=np.double)
        return array

    def get_best_model(self):
        model = []
        for index in range(len(self._feature_combinations)):
            model_feature_combination = self._get_best_model_feature_combination(index)
            model.append(model_feature_combination)

        return model

    def _get_current_model_feature_combination(self, feature_combination_index):
        """ Returns current model/function according to validation set
            for a given feature combination.

        Args:
            feature_combination_index: The index for the feature combination.

        Returns:
            An ndarray that represents the model.
        """

        if self._model_type == "classification" and self._n_classes <= 1:
            # if there is only one legal state for a classification problem, then we know with 100%
            # certainty what the result will be, and our logits for that result should be infinity
            # since we reduce the number of logits by 1, we would get back an empty array from the C code
            # after we expand the model for our caller, the tensor's dimensions should match
            # the features for the feature_combination, but the last class_index should have a dimension
            # of 1 for the infinities.  This all needs to be special cased anyways, so we can just return
            # a None value here for now and handle in the upper levels
            #
            # If we were to allow datasets with zero instances, then it would also be legal for there
            # to be 0 states.  We can probably handle this the same as having 1 state though since 
            # any instances in any evaluations need to have a state

            # TODO PK make sure the None value here is handled by our caller
            return None

        array_p = self._native.lib.GetCurrentModelFeatureCombination(
            self._model_pointer, feature_combination_index
        )

        if not array_p:  # pragma: no cover
            raise MemoryError("Out of memory in GetCurrentModelFeatureCombination")

        shape = self._get_feature_combination_shape(feature_combination_index)

        array = Native.make_ndarray(array_p, shape, dtype=np.double)
        return array

    def get_current_model(self):
        model = []
        for index in range(len(self._feature_combinations)):
            model_feature_combination = self._get_current_model_feature_combination(index)
            model.append(model_feature_combination)

        return model


class NativeEBMInteraction:
    """Lightweight wrapper for EBM C interaction code.
    """

    def __init__(
        self,
        model_type,
        n_classes,
        features,
        X,
        y,
        scores,
    ):

        """ Initializes internal wrapper for EBM C code.

        Args:
            model_type: 'regression'/'classification'.
            n_classes: Specific to classification,
                number of unique classes.
            features: List of features represented individually as
                dictionary of keys ('type', 'has_missing', 'n_bins').
            X: Training design matrix as 2-D ndarray.
            y: Training response as 1-D ndarray.
            scores: predictions from a prior predictor.  For regression
                there is 1 prediction per instance.  For binary classification
                there is one logit.  For multiclass there are n_classes logits

        """

        # first set the one thing that we will close on
        self._interaction_pointer = None

        self._native = Native.get_native_singleton()

        log.info("Allocation interaction start")

        # Store args
        feature_array = Native.convert_features_to_c(features)

        if scores is None:
            n_scores = EBMUtils.get_count_scores_c(n_classes)
            scores = np.zeros(y.shape[0] * n_scores, dtype=np.float64, order='C')

        # Allocate external resources
        if model_type == "classification":
            self._interaction_pointer = self._native.lib.InitializeInteractionClassification(
                n_classes,
                len(feature_array),
                feature_array,
                len(y),
                X,
                y,
                scores,
            )
            if not self._interaction_pointer:  # pragma: no cover
                raise MemoryError("Out of memory in InitializeInteractionClassification")
        elif model_type == "regression":
            self._interaction_pointer = self._native.lib.InitializeInteractionRegression(
                len(feature_array),
                feature_array,
                len(y),
                X,
                y,
                scores,
            )
            if not self._interaction_pointer:  # pragma: no cover
                raise MemoryError("Out of memory in InitializeInteractionRegression")
        else:
            raise AttributeError("Unrecognized model_type")

        log.info("Allocation interaction end")

    def close(self):
        """ Deallocates C objects used to determine interactions in EBM. """
        log.info("Deallocation interaction start")
        self._native.lib.FreeInteraction(self._interaction_pointer)
        log.info("Deallocation interaction end")

    def get_interaction_score(self, feature_index_tuple):
        """ Provides score for an feature interaction. Higher is better."""
        log.info("Fast interaction score start")
        score = ct.c_double(0.0)
        return_code = self._native.lib.GetInteractionScore(
            self._interaction_pointer,
            len(feature_index_tuple),
            np.array(feature_index_tuple, dtype=np.int64),
            ct.byref(score),
        )
        if return_code != 0:  # pragma: no cover
            raise Exception("Out of memory in GetInteractionScore")

        log.info("Fast interaction score end")
        return score.value

class NativeHelper:
    @staticmethod
    def cyclic_gradient_boost(
        model_type,
        n_classes,
        features,
        feature_combinations,
        X_train,
        y_train,
        scores_train,
        X_val,
        y_val,
        scores_val,
        n_inner_bags,
        random_state,
        learning_rate,
        max_tree_splits,
        min_cases_for_splits,
        training_step_episodes,
        data_n_episodes,
        early_stopping_tolerance,
        early_stopping_run_length,
        name
    ):

        min_metric = np.inf
        episode_index = 0
        with closing(
            NativeEBMTraining(
                model_type,
                n_classes,
                features,
                feature_combinations,
                X_train,
                y_train,
                scores_train,
                X_val,
                y_val,
                scores_val,
                n_inner_bags,
                random_state
            )
        ) as native_ebm_training:
            no_change_run_length = 0
            bp_metric = np.inf
            log.info("Start boosting {0}".format(name))
            for episode_index in range(data_n_episodes):
                if episode_index % 10 == 0:
                    log.debug("Sweep Index for {0}: {1}".format(name, episode_index))
                    log.debug("Metric: {0}".format(min_metric))

                for feature_combination_index in range(len(feature_combinations)):
                    curr_metric = native_ebm_training.training_step(
                        feature_combination_index=feature_combination_index,
                        learning_rate=learning_rate,
                        max_tree_splits=max_tree_splits,
                        min_cases_for_split=min_cases_for_splits,
                        training_step_episodes=training_step_episodes,
                    )

                    min_metric = min(curr_metric, min_metric)

                # TODO PK this early_stopping_tolerance is a little inconsistent
                #      since it only exits when a small range of figures expresses
                #      a pattern, but we can do better by keeping a list of the last
                #      number of measurements to have a consistent window of values
                if no_change_run_length == 0:
                    bp_metric = min_metric
                if min_metric + early_stopping_tolerance < bp_metric:
                    no_change_run_length = 0
                else:
                    no_change_run_length += 1

                if (
                    early_stopping_run_length >= 0
                    and no_change_run_length >= early_stopping_run_length
                ):
                    break

            log.info("End boosting {0}, Best Metric: {1}, Num Rounds: {2}".format(name, min_metric, episode_index))
            model_update = native_ebm_training.get_best_model()

        return model_update, min_metric, episode_index

    @staticmethod
    def get_interactions(
        n_interactions,
        iter_feature_combinations,
        model_type,
        n_classes,
        features,
        X,
        y,
        scores
    ):
        # TODO PK we only need to store the top n_interactions items, so use a heap
        interaction_scores = []
        with closing(
            NativeEBMInteraction(
                model_type=model_type,
                n_classes=n_classes,
                features=features,
                X=X,
                y=y,
                scores=scores,
            )
        ) as native_ebm_interactions:
            for feature_combination in iter_feature_combinations:
                score = native_ebm_interactions.get_interaction_score(feature_combination)
                interaction_scores.append((feature_combination, score))

        ranked_scores = list(
            sorted(interaction_scores, key=lambda x: x[1], reverse=True)
        )
        n_interactions = min(len(ranked_scores), n_interactions)
        final_ranked_scores = ranked_scores[0:n_interactions]

        final_indices = [x[0] for x in final_ranked_scores]
        final_scores = [x[1] for x in final_ranked_scores]

        return final_indices, final_scores
