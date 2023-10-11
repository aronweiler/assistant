param (
    [string]$overrideVersion
)

# Read the current version from version.txt
$currentVersion = Get-Content -Path version.txt
Write-Host "Current version is $currentVersion"

# If an override version is provided, use it; otherwise, increment the minor version
if ($overrideVersion) {
    $newVersion = $overrideVersion
    Write-Host "Overriding version to $newVersion"
} else {
    $versionParts = $currentVersion.Split('.')
    $majorVersion = [int]$versionParts[0]
    $minorVersion = [int]$versionParts[1] + 1
    $newVersion = "$majorVersion.$minorVersion"
    Write-Host "Incrementing version to $newVersion"

    # Write the new version back to version.txt
    $newVersion | Set-Content -Path version.txt
}

# Update the Docker tags
Write-Host "Updating Docker tags to $newVersion"
$latestTag = "aronweiler/assistant:latest"
$newTag = "aronweiler/assistant:$newVersion"

# Build and tag the Docker image
docker build -t $latestTag .
docker tag $latestTag $newTag

# Push the Docker images -- uncomment for production
docker push $latestTag
docker push $newTag
