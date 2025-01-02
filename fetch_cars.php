<?php
// fetch_cars.php
try {
    // Connect to the SQLite database
    // Ensure to replace backslashes with double backslashes or forward slashes in your path
    $db = new PDO('sqlite:C:\\Users\\ZQureshi\\OneDrive - North London Collegiate School (NLCS)\\Documents\\FIN Website\\finDB.sqlite');
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // Define your SELECT query
    $query = "SELECT Make, Model, Price FROM Cars";

    // Execute the query and get the result set
    $result = $db->query($query);

    // Initialize an empty string to hold your HTML output
    $output = "";

    // Loop through the result set and build your HTML output
    foreach ($result as $row) {
        $output .= "<div>";
        $output .= "<h2>" . htmlspecialchars($row['Make']) . " " . htmlspecialchars($row['Model']) . "</h2>";
        $output .= "<p>Price: $" . htmlspecialchars($row['Price']) . "</p>";
        $output .= "</div>";
    }
    
    // Print the HTML output
    echo $output;
} catch (PDOException $e) {
    // Handle any errors
    echo "An error occurred: " . $e->getMessage();
}
?>
