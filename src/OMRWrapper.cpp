#include "OMRWrapper.h"
#include <stdexcept>
#include <filesystem>

OMRWrapper::OMRWrapper() : jvm(nullptr), env(nullptr), audiverisClass(nullptr) {
	initJVM();
	findAudiverisClass();
}

OMRWrapper::~OMRWrapper() {
	cleanup();
}

void OMRWrapper::initJVM() {
	JavaVMInitArgs vm_args;
	JavaVMOption options[3];
	
	std::string classpath = "-Djava.class.path=";
	classpath += std::filesystem::absolute("external/audiveris/build/jar/audiveris.jar").string();
	
	options[0].optionString = const_cast<char*>(classpath.c_str());
	options[1].optionString = const_cast<char*>("-Djava.awt.headless=true");
	options[2].optionString = const_cast<char*>("--add-exports=java.desktop/sun.awt.image=ALL-UNNAMED");
	
	vm_args.version = JNI_VERSION_1_8;
	vm_args.nOptions = 3;
	vm_args.options = options;
	vm_args.ignoreUnrecognized = JNI_FALSE;
	
	jint res = JNI_CreateJavaVM(&jvm, (void**)&env, &vm_args);
	if (res != JNI_OK || !env) {
		throw std::runtime_error("Failed to create Java VM");
	}
}

void OMRWrapper::findAudiverisClass() {
	jclass localClass = env->FindClass("org/audiveris/omr/Main");
	if (!localClass) {
		throw std::runtime_error("Failed to find Audiveris Main class");
	}
	
	audiverisClass = (jclass)env->NewGlobalRef(localClass);
	env->DeleteLocalRef(localClass);
	
	processMethod = env->GetStaticMethodID(audiverisClass, "processPage", 
		"(Ljava/lang/String;I)Ljava/lang/String;");
	if (!processMethod) {
		throw std::runtime_error("Failed to find processPage method");
	}
	
	convertMethod = env->GetStaticMethodID(audiverisClass, "convertToMidi",
		"(Ljava/lang/String;)Ljava/lang/String;");
	if (!convertMethod) {
		throw std::runtime_error("Failed to find convertToMidi method");
	}
}

std::string OMRWrapper::processPage(const std::string& pdfPath, int pageNum) {
	jstring jPdfPath = env->NewStringUTF(pdfPath.c_str());
	jstring result = (jstring)env->CallStaticObjectMethod(audiverisClass, processMethod, 
		jPdfPath, pageNum);
	
	if (!result) {
		env->DeleteLocalRef(jPdfPath);
		return "";
	}
	
	const char* cResult = env->GetStringUTFChars(result, nullptr);
	std::string output(cResult);
	
	env->ReleaseStringUTFChars(result, cResult);
	env->DeleteLocalRef(jPdfPath);
	env->DeleteLocalRef(result);
	
	return output;
}

std::string OMRWrapper::convertToMidi(const std::string& musicXmlPath) {
	jstring jXmlPath = env->NewStringUTF(musicXmlPath.c_str());
	jstring result = (jstring)env->CallStaticObjectMethod(audiverisClass, convertMethod, jXmlPath);
	
	if (!result) {
		env->DeleteLocalRef(jXmlPath);
		return "";
	}
	
	const char* cResult = env->GetStringUTFChars(result, nullptr);
	std::string output(cResult);
	
	env->ReleaseStringUTFChars(result, cResult);
	env->DeleteLocalRef(jXmlPath);
	env->DeleteLocalRef(result);
	
	return output;
}

bool OMRWrapper::hasMusicNotation(const std::string& pdfPath, int pageNum) {
	return !processPage(pdfPath, pageNum).empty();
}

void OMRWrapper::cleanup() {
	if (env && audiverisClass) {
		env->DeleteGlobalRef(audiverisClass);
	}
	if (jvm) {
		jvm->DestroyJavaVM();
	}
}