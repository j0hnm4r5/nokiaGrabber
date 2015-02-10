#include "ofApp.h"

//--------------------------------------------------------------
void ofApp::setup(){

	ofDisableArbTex();
	ofEnableBlendMode(OF_BLENDMODE_ALPHA);
	glShadeModel(GL_SMOOTH);

	python.init();
	python.executeScript("sandbox.py");
	
	ofxPythonObject myApp = python.getObject("MyApp");
	
	float lat = 40.709620;
	float lon = -74.009086;
	float zoom = 19;
	
	if (myApp) {
		python_program = myApp();
	}
	if (python_program) {
		python_program.attr("lat") = python.evalString(ofToString(lat));
		python_program.attr("lon") = python.evalString(ofToString(lon));
		python_program.attr("zoom") = python.evalString(ofToString(zoom));
		
		python_program.method("go");
		
		model.loadModel("objs/LAT" + ofToString((int)lat) + "_LON" + ofToString((int)lon) + "_Z" + ofToString((int)zoom) + ".obj");
		
		for (int i = 0; i < model.getNumMeshes(); i++) {
			model.getMesh(i).getVertices();
		}
		
		
		
		base.set(model.getSceneMax().x - model.getSceneMin().x, model.getSceneMax().y - model.getSceneMin().y);
	}
	
	cam.setDistance(1000);
}

//--------------------------------------------------------------
void ofApp::update(){


}

//--------------------------------------------------------------
void ofApp::draw(){

	ofSetColor(255);

	
	ofEnableDepthTest();
	ofEnableSeparateSpecularLight();
	ofEnableLighting();
	light.enable();
	light.setDirectional();
	light.setOrientation(ofVec3f(45, 90));
	
	cam.begin();

	model.setPosition(model.getSceneCenter().x, model.getSceneCenter().y, 0);
	model.drawFaces();

	
//	ofSetColor(255, 0, 100);
//	base.setPosition(0, 0, 0);
//	base.setResolution(2, 2);
//	base.draw();
	
	cam.end();
	
	
	light.disable();
	ofDisableLighting();
	ofDisableSeparateSpecularLight();
	ofDisableDepthTest();


}

//--------------------------------------------------------------
void ofApp::keyPressed(int key){

}

//--------------------------------------------------------------
void ofApp::keyReleased(int key){

}

//--------------------------------------------------------------
void ofApp::mouseMoved(int x, int y ){

}

//--------------------------------------------------------------
void ofApp::mouseDragged(int x, int y, int button){

}

//--------------------------------------------------------------
void ofApp::mousePressed(int x, int y, int button){

}

//--------------------------------------------------------------
void ofApp::mouseReleased(int x, int y, int button){

}

//--------------------------------------------------------------
void ofApp::windowResized(int w, int h){

}

//--------------------------------------------------------------
void ofApp::gotMessage(ofMessage msg){

}

//--------------------------------------------------------------
void ofApp::dragEvent(ofDragInfo dragInfo){ 

}
