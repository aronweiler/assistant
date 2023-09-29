# Read the current version from version.txt
$currentVersion = Get-Content -Path version.txt

# Increment the version
$versionParts = $currentVersion.Split('.')
$majorVersion = [int]$versionParts[0]
$minorVersion = [int]$versionParts[1] + 1

$newVersion = "$majorVersion.$minorVersion"

# Write the new version back to version.txt
$newVersion | Set-Content -Path version.txt

# Update the Docker tags
$latestTag = "aronweiler/assistant:latest"
$newTag = "aronweiler/assistant:$newVersion"

# Build and tag the Docker image
docker build -t $latestTag .
docker tag $latestTag $newTag

# Push the Docker images -- uncomment for production
docker push $latestTag
docker push $newTag