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
}
else {
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

# Configuration for retry
$maxRetries = 5 # Default number of retries
$retryDelaySeconds = 2 # Delay between retries

# Attempt to build the Docker image with retries
$retryCount = 0
$buildSucceeded = $false
while ($retryCount -lt $maxRetries -and -not $buildSucceeded) {
    docker build -t $latestTag .
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Docker build succeeded after $($retryCount + 1) attempt(s)"
        $buildSucceeded = $true
    }
    else {
        Write-Host "Docker build failed, attempt #$($retryCount + 1) of $maxRetries"
        Start-Sleep -Seconds $retryDelaySeconds
        $retryCount++
    }
}

if (-not $buildSucceeded) {
    Write-Host "Docker build failed after $maxRetries attempts, skipping tagging and pushing."
}
else {
    Write-Host "Proceeding with tagging and pushing."
    docker tag $latestTag $newTag
    # Push the Docker images -- uncomment for production
    docker push $latestTag
    docker push $newTag
}