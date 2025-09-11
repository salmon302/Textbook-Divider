#include <gtest/gtest.h>
#include "../src/TextProcessor.h"

class TextProcessorTest : public ::testing::Test {
protected:
	TextProcessor processor;
};

TEST_F(TextProcessorTest, RemoveOCRArtifacts) {
	std::string input = "Hello© World™ \x0C Test®";
	std::string expected = "Hello World \n Test";
	EXPECT_EQ(processor.cleanText(input), expected);
}

TEST_F(TextProcessorTest, RemoveExtraWhitespace) {
	std::string input = "Hello    World\t\t\nTest    Example";
	std::string expected = "Hello World Test Example";
	EXPECT_EQ(processor.cleanText(input), expected);
}

TEST_F(TextProcessorTest, FixCommonOCRErrors) {
	std::string input = "l am reading. The rn0use ran.";
	std::string expected = "I am reading. The mouse ran.";
	EXPECT_EQ(processor.cleanText(input), expected);
}

TEST_F(TextProcessorTest, PreserveMathFormulas) {
	std::string input = "The equation $x^2 + y^2 = z^2$ is Pythagorean.";
	std::string expected = "The equation $x^2 + y^2 = z^2$ is Pythagorean.";
	EXPECT_EQ(processor.formatText(input), expected);
}

TEST_F(TextProcessorTest, FormatParagraphs) {
	std::string input = "First line.\nSecond line.\n\nNew paragraph.\nContinued.";
	std::string expected = "First line. Second line.\n\nNew paragraph. Continued.\n";
	EXPECT_EQ(processor.formatText(input), expected);
}

TEST_F(TextProcessorTest, HandleTablesFigures) {
	std::string input = "Text before\nTable 1: Sample Data\nText after";
	std::string expected = "Text before\n\nTable 1: Sample Data\n\nText after";
	EXPECT_EQ(processor.formatText(input), expected);
}

TEST_F(TextProcessorTest, ComplexTextProcessing) {
	std::string input = "Chapter l:\nThe rn0use    ran\n\nTable 1: Data\n$x^2$";
	std::string expected = "Chapter I:\nThe mouse ran\n\nTable 1: Data\n\n$x^2$";
	std::string result = processor.cleanText(input);
	result = processor.formatText(result);
	EXPECT_EQ(result, expected);
}

int main(int argc, char **argv) {
	testing::InitGoogleTest(&argc, argv);
	return RUN_ALL_TESTS();
}