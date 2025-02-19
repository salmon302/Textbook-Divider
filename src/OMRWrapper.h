#pragma once

#include <jni.h>
#include <string>
#include <vector>
#include <memory>

class OMRWrapper {
public:
	OMRWrapper();
	~OMRWrapper();

	// Process a page and return MusicXML if music notation is found
	std::string processPage(const std::string& pdfPath, int pageNum);
	
	// Convert MusicXML to MIDI
	std::string convertToMidi(const std::string& musicXmlPath);

	// Check if a page contains music notation
	bool hasMusicNotation(const std::string& pdfPath, int pageNum);

private:
	JavaVM* jvm;
	JNIEnv* env;
	jclass audiverisClass;
	jmethodID processMethod;
	jmethodID convertMethod;
	
	void initJVM();
	void findAudiverisClass();
	void cleanup();
};