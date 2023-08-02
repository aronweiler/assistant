# Load the db.env file into the environment using powershell commands
$envFile = 'db.env'

# Read the contents of db.env
$content = Get-Content $envFile

# Loop through each line and set the environment variables
foreach ($line in $content) {
    # Split the line by '=' to get the key and value
    $key, $value = $line -split '=', 2

    # Set the environment variable
    [Environment]::SetEnvironmentVariable($key, $value, 'User')
}

