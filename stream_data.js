const DEBUG_DATA = false;
const IMAGE_URL = "https://dnaspaces.io/api/location/v1/map/images/floor/"

/**
 * Fetch and process the stream
 */
async function process() {
    // Retrieve NDJSON from the server
    console.log("Processing...")
    var token = "2027B27659EE4F1C8B8DDE8CAA974154"
    const response = await fetch("https://partners.dnaspaces.io/api/partners/v1/firehose/events", {
            headers: new Headers({
                "X-API-Key": token
            })});
    console.log("API called.")
    const reader = response.body.getReader();
    const { value, done } = reader.read();

    if (done) {
      console.log("The stream was already closed!");
    } else {
      console.log(value);
    }
}

/**
 * Read through the results and write to the DOM
 * @param {object} reader
 */
function writeToDOM(reader) {
    console.log("Writing data")
    reader.read().then(
        ({ value, done }) => {
            if (done) {
                console.log("The stream was already closed!");

            } else {
                // Build up the values
                console.log(value);
                let result = document.createElement('div');
                console.log(value['deviceLocationUpdate']['device']['macAddress']);
                result.innerHTML = `<div>ID: ${value.id} - Phone: ${value.phone} - Result: ${value.result}</div><br>`;

                // Prepend to the target
                targetDiv.insertBefore(result, targetDiv.firstChild);

                // Recursively call
                writeToDOM(reader);
            }
        },
        e => console.error("The stream became errored and cannot be read from!", e)
    );
}

function create_table(table_data) {
    console.log("create_table(): Creating table with data. Total records ", table_data.length);
    let formatDecimalComma = d3.format(",.2f")
    d3.select("#floor_count_table").select("table").remove();
    var headers = [
        "Reference",
        "Campus",
        "Building Name",
        "Floor Name",
        "Floor Id",
        "Width",
        "Length",
        "Count"
    ]
    d3.select("#floor_count_table")
        .append("table").attr("class", "table table-responsive-sm table-hover")
        .append("tbody");

    d3.select("tbody")
        .selectAll("th")
        .data(headers)
        .enter()
        .append("th")
        .text(function(d){
            return d
        });
    // fill the table
    // create rows
    var tr = d3.select("tbody").selectAll("tr")
        .data(table_data)
        .enter()
        .append("tr")
        .on("click", function(d) {
            $(this).addClass('table-dark').siblings().removeClass('table-dark');
            console.log("create_table() on-click ", d.imageName, d.floorName, d.floorId, d.width, d.length);
            fetchImageAndDisplay(d.imageName, d.floorName, d.floorId, d.width, d.length);
        });
    // cells
    var found_first_image = false;
    tr.each(function(d, i) {
        if (found_first_image == false){
            $(this).addClass('table-dark').siblings().removeClass('table-dark');
            fetchImageAndDisplay(d.imageName, d.floorName, d.floorId, d.width, d.length);
            found_first_image = true;
            console.log("Getting first row image", d.imageName);
        }
       	var self = d3.select(this);
            self.append("td")
                .text(i);
            self.append("td")
                .text(d.campus);
            self.append("td")
                .text(d.building);
            self.append("td")
                .text(d.floorName);
            self.append("td")
                .text(d.floorId);
            self.append("td")
                .text(formatDecimalComma(d.width));
            self.append("td")
                .text(formatDecimalComma(d.length));
        	self.append("td")
        		.text(d.count);
      });
    return;
};





