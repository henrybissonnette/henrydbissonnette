

var drawingCanvas = document.getElementById('myDrawing');
// Check the element is in the DOM and the browser supports canvas
if(drawingCanvas.getContext) {
	// Initaliase a 2-dimensional drawing context
	var context = drawingCanvas.getContext('2d');
	//Canvas commands go here
	// Create the yellow face
	context.strokeStyle = "#000000";
	context.fillStyle = "#FFFF00";
	context.beginPath();
	context.arc(100,100,50,0,Math.PI*2,true);
	context.closePath();
	context.stroke();
	context.fill();
}