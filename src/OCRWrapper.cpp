#include "OCRWrapper.h"
#include <Python.h>
#include <stdexcept>
#include <iostream>

OCRWrapper::OCRWrapper() : pModule(nullptr), pOCRClass(nullptr), pOCRInstance(nullptr),
						  pOMRClass(nullptr), pOMRInstance(nullptr) {
	Py_Initialize();
	// Import sys module for path manipulation
	PyRun_SimpleString("import sys");
	// Add virtual environment site-packages
	std::string pythonPath = 
		std::string("import sys\n") +
		"sys.path.append('" + std::string(SOURCE_DIR) + "/venv/lib/python3.12/site-packages')\n" +
		"sys.path.append('" + std::string(SOURCE_DIR) + "/src')\n" +
		"sys.path.append('" + std::string(BINARY_DIR) + "')\n";
	PyRun_SimpleString(pythonPath.c_str());
}

OCRWrapper::~OCRWrapper() {
	cleanup();
	Py_Finalize();
}

void OCRWrapper::cleanup() {
	if (pOMRInstance) {
		Py_DECREF(pOMRInstance);
		pOMRInstance = nullptr;
	}
	if (pOMRClass) {
		Py_DECREF(pOMRClass);
		pOMRClass = nullptr;
	}
	if (pOCRInstance) {
		Py_DECREF(pOCRInstance);
		pOCRInstance = nullptr;
	}
	if (pOCRClass) {
		Py_DECREF(pOCRClass);
		pOCRClass = nullptr;
	}
	if (pModule) {
		Py_DECREF(pModule);
		pModule = nullptr;
	}
}

bool OCRWrapper::initialize(const std::string& lang, bool enable_gpu) {
	// Add source and build directories to Python path
	std::string pythonPath = 
		std::string("import sys\n") +
		"print('Current working directory:', __import__('os').getcwd())\n" +
		"print('SOURCE_DIR:', '" + std::string(SOURCE_DIR) + "')\n" +
		"print('BINARY_DIR:', '" + std::string(BINARY_DIR) + "')\n" +
		"sys.path.append('" + std::string(SOURCE_DIR) + "/src')\n" +
		"sys.path.append('" + std::string(BINARY_DIR) + "')\n" +
		"print('Python paths:', sys.path)\n" +
		"print('Attempting to import textbook_divider.ocr_processor...')\n";
	PyRun_SimpleString(pythonPath.c_str());
	
	PyObject* pName = PyUnicode_FromString("textbook_divider.ocr_processor");
	pModule = PyImport_Import(pName);
	Py_DECREF(pName);
	
	if (!pModule) {
		PyErr_Print();
		return false;
	}
	
	pOCRClass = PyObject_GetAttrString(pModule, "OCRProcessor");
	if (!pOCRClass) {
		PyErr_Print();
		cleanup();
		return false;
	}
	
	PyObject* pArgs = PyTuple_New(2);
	PyTuple_SetItem(pArgs, 0, PyUnicode_FromString(lang.c_str()));
	PyTuple_SetItem(pArgs, 1, PyBool_FromLong(enable_gpu));
	
	pOCRInstance = PyObject_CallObject(pOCRClass, pArgs);
	Py_DECREF(pArgs);
	
	if (!pOCRInstance) {
		PyErr_Print();
		cleanup();
		return false;
	}
	
	return true;
}

std::string OCRWrapper::processImage(const std::string& imagePath) {
	if (!pOCRInstance) {
		return "";
	}
	
	PyObject* pArgs = PyTuple_New(1);
	PyTuple_SetItem(pArgs, 0, PyUnicode_FromString(imagePath.c_str()));
	
	PyObject* pResult = PyObject_CallMethodObjArgs(pOCRInstance, 
		PyUnicode_FromString("process_image"), 
		PyTuple_GetItem(pArgs, 0), 
		NULL);
	Py_DECREF(pArgs);
	
	if (!pResult) {
		PyErr_Print();
		return "";
	}
	
	const char* result = PyUnicode_AsUTF8(pResult);
	std::string text = result ? result : "";
	Py_DECREF(pResult);
	
	return text;
}

std::string OCRWrapper::processImages(const std::vector<std::string>& imagePaths) {
	if (!pOCRInstance) {
		return "";
	}
	
	PyObject* pImageList = PyList_New(imagePaths.size());
	for (size_t i = 0; i < imagePaths.size(); ++i) {
		PyList_SetItem(pImageList, i, PyUnicode_FromString(imagePaths[i].c_str()));
	}
	
	PyObject* pResult = PyObject_CallMethodObjArgs(pOCRInstance,
		PyUnicode_FromString("process_images"),
		pImageList,
		NULL);
	Py_DECREF(pImageList);
	
	if (!pResult) {
		PyErr_Print();
		return "";
	}
	
	const char* result = PyUnicode_AsUTF8(pResult);
	std::string text = result ? result : "";
	Py_DECREF(pResult);
	
	return text;
}

std::string OCRWrapper::extractTextWithFallback(const std::string& pdfPath, int pageNum) {
    if (!pOCRInstance) {
        return "";
    }
    
    PyObject* pArgs = PyTuple_New(2);
    PyTuple_SetItem(pArgs, 0, PyUnicode_FromString(pdfPath.c_str()));
    PyTuple_SetItem(pArgs, 1, PyLong_FromLong(pageNum));
    
    PyObject* pResult = PyObject_CallMethodObjArgs(pOCRInstance,
        PyUnicode_FromString("extract_text_with_fallback"),
        PyTuple_GetItem(pArgs, 0),
        PyTuple_GetItem(pArgs, 1),
        NULL);
    Py_DECREF(pArgs);
    
    if (!pResult) {
        PyErr_Print();
        return "";
    }
    
    const char* result = PyUnicode_AsUTF8(pResult);
    std::string text = result ? result : "";
    Py_DECREF(pResult);
    
    return text;
}

std::map<std::string, bool> OCRWrapper::detectFeatures(const std::string& text) {
	if (!pOCRInstance) {
		return {{"math", false}, {"music", false}};
	}
	
	PyObject* pArgs = PyTuple_New(1);
	PyTuple_SetItem(pArgs, 0, PyUnicode_FromString(text.c_str()));
	
	PyObject* pResult = PyObject_CallMethodObjArgs(pOCRInstance,
		PyUnicode_FromString("detect_features"),
		PyTuple_GetItem(pArgs, 0),
		NULL);
	Py_DECREF(pArgs);
	
	if (!pResult || !PyDict_Check(pResult)) {
		PyErr_Print();
		return {{"math", false}, {"music", false}};
	}
	
	std::map<std::string, bool> features;
	PyObject *key, *value;
	Py_ssize_t pos = 0;
	
	while (PyDict_Next(pResult, &pos, &key, &value)) {
		const char* feature_name = PyUnicode_AsUTF8(key);
		int feature_value = PyObject_IsTrue(value);
		if (feature_name) {
			features[feature_name] = feature_value == 1;
		}
	}
	
	Py_DECREF(pResult);
	return features;
}

bool OCRWrapper::initializeOMR(const std::string& audiverisPath) {
	try {
		PyObject* pName = PyUnicode_FromString("textbook_divider.omr_processor");
		PyObject* pOMRModule = PyImport_Import(pName);
		Py_DECREF(pName);
		
		if (!pOMRModule) {
			PyErr_Print();
			return false;
		}
		
		pOMRClass = PyObject_GetAttrString(pOMRModule, "OMRProcessor");
		Py_DECREF(pOMRModule);
		
		if (!pOMRClass) {
			PyErr_Print();
			return false;
		}
		
		if (!audiverisPath.empty()) {
			PyObject* args = PyTuple_Pack(1, PyUnicode_FromString(audiverisPath.c_str()));
			pOMRInstance = PyObject_CallObject(pOMRClass, args);
			Py_DECREF(args);
		} else {
			pOMRInstance = PyObject_CallObject(pOMRClass, nullptr);
		}
		
		if (!pOMRInstance) {
			PyErr_Print();
			return false;
		}
		
		return true;
	} catch (const std::exception& e) {
		std::cerr << "OMR initialization error: " << e.what() << std::endl;
		return false;
	}
}

OCRWrapper::OMRResult OCRWrapper::processPageWithOMR(const std::string& pdfPath, int pageNum) {
	OMRResult result{false, false, "", "", "", "OMR not initialized"};
	
	if (!pOMRInstance) {
		return result;
	}
	
	try {
		PyObject* args = PyTuple_Pack(2,
			PyUnicode_FromString(pdfPath.c_str()),
			PyLong_FromLong(pageNum)
		);
		
		PyObject* pResult = PyObject_CallMethodObjArgs(
			pOMRInstance,
			PyUnicode_FromString("process_page"),
			PyTuple_GetItem(args, 0),
			PyTuple_GetItem(args, 1),
			NULL
		);
		Py_DECREF(args);
		
		if (!pResult) {
			PyErr_Print();
			return result;
		}
		
		result = parseOMRResult(pResult);
		Py_DECREF(pResult);
		
	} catch (const std::exception& e) {
		result.error = e.what();
	}
	
	return result;
}

OCRWrapper::OMRResult OCRWrapper::parseOMRResult(PyObject* result) {
	OMRResult omrResult{false, false, "", "", "", ""};
	
	if (!PyDict_Check(result)) {
		omrResult.error = "Invalid result type";
		return omrResult;
	}
	
	PyObject* success = PyDict_GetItemString(result, "success");
	PyObject* hasMusic = PyDict_GetItemString(result, "has_music");
	PyObject* text = PyDict_GetItemString(result, "text");
	PyObject* musicxml = PyDict_GetItemString(result, "musicxml");
	PyObject* midi = PyDict_GetItemString(result, "midi");
	PyObject* error = PyDict_GetItemString(result, "error");
	
	omrResult.success = success && PyObject_IsTrue(success);
	omrResult.hasMusic = hasMusic && PyObject_IsTrue(hasMusic);
	
	if (text && PyUnicode_Check(text)) {
		omrResult.text = PyUnicode_AsUTF8(text);
	}
	
	if (musicxml && PyUnicode_Check(musicxml)) {
		omrResult.musicXML = PyUnicode_AsUTF8(musicxml);
	}
	
	if (midi && PyUnicode_Check(midi)) {
		omrResult.midi = PyUnicode_AsUTF8(midi);
	}
	
	if (error && PyUnicode_Check(error)) {
		omrResult.error = PyUnicode_AsUTF8(error);
	}
	
	return omrResult;
}