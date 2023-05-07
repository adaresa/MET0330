<?php

// Loop through and grab variables from the received URL
foreach ($_REQUEST as $key => $value) {
    if ($key == "id") {
        $unit = $value;
    }
}

include("database_connect.php");

// Check the connection
if (mysqli_connect_errno()) {
    echo "Failed to connect to MySQL: " . mysqli_connect_error();
}

// Get all the values from the table in the database
$result = mysqli_query($con, "SELECT * FROM room_presence WHERE id = '$unit'");

$data = array(); // Initialize an empty array to store the fetched data

while ($row = mysqli_fetch_assoc($result)) {
    $data[] = $row; // Add the row to the data array
}

// Convert the data array to a JSON format and output it
echo json_encode($data[0]); // First element of the array is the only element

?>
