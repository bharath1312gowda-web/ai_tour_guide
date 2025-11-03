class GPSController {
    constructor() {
        this.currentPosition = null;
        this.watchId = null;
        this.isTracking = false;
        this.destination = null;
        this.navigationActive = false;
    }

    initializeGPS() {
        if (!navigator.geolocation) {
            console.error('Geolocation is not supported by this browser.');
            this.showGPSError('Geolocation is not supported by your browser.');
            return;
        }

        this.startTracking();
    }

    startTracking() {
        const options = {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0
        };

        this.watchId = navigator.geolocation.watchPosition(
            (position) => this.handlePositionUpdate(position),
            (error) => this.handlePositionError(error),
            options
        );

        this.isTracking = true;
        this.updateGPSUI(true);
    }

    stopTracking() {
        if (this.watchId) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }
        this.isTracking = false;
        this.navigationActive = false;
        this.updateGPSUI(false);
    }

    handlePositionUpdate(position) {
        this.currentPosition = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            timestamp: position.timestamp
        };

        window.currentCoordinates = [this.currentPosition.latitude, this.currentPosition.longitude];
        
        this.updateLocationDisplay();
        
        if (this.navigationActive && this.destination) {
            this.updateNavigationInfo();
        }

        // Emit position update to server if needed
        if (window.tourGuideApp && window.tourGuideApp.socket) {
            window.tourGuideApp.socket.emit('position_update', {
                coordinates: window.currentCoordinates,
                user_id: window.tourGuideApp.userId
            });
        }
    }

    handlePositionError(error) {
        console.error('Geolocation error:', error);
        
        let errorMessage = 'Unable to retrieve your location. ';
        
        switch(error.code) {
            case error.PERMISSION_DENIED:
                errorMessage += 'Please enable location permissions in your browser settings.';
                break;
            case error.POSITION_UNAVAILABLE:
                errorMessage += 'Location information is unavailable.';
                break;
            case error.TIMEOUT:
                errorMessage += 'Location request timed out.';
                break;
            default:
                errorMessage += 'An unknown error occurred.';
                break;
        }
        
        this.showGPSError(errorMessage);
        this.updateGPSUI(false);
    }

    updateLocationDisplay() {
        const locationElement = document.getElementById('current-location');
        if (locationElement && this.currentPosition) {
            const lat = this.currentPosition.latitude.toFixed(4);
            const lng = this.currentPosition.longitude.toFixed(4);
            locationElement.innerHTML = `
                <i class="fas fa-map-marker-alt"></i>
                <span>Lat: ${lat}, Lng: ${lng}</span>
            `;
        }
    }

    updateNavigationInfo() {
        if (!this.currentPosition || !window.tourGuideApp?.currentDestination) return;

        const destination = DESTINATIONS[window.tourGuideApp.currentDestination];
        if (!destination) return;

        const startCoords = [this.currentPosition.latitude, this.currentPosition.longitude];
        const endCoords = destination.coordinates;

        // Calculate distance
        const distance = this.calculateDistance(startCoords, endCoords);
        
        // Calculate bearing
        const bearing = this.calculateBearing(startCoords, endCoords);
        
        this.displayNavigationInfo(distance, bearing, destination.name);
    }

    calculateDistance(coords1, coords2) {
        const [lat1, lon1] = coords1;
        const [lat2, lon2] = coords2;
        
        const R = 6371; // Earth's radius in kilometers
        const dLat = this.toRad(lat2 - lat1);
        const dLon = this.toRad(lon2 - lon1);
        
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(this.toRad(lat1)) * Math.cos(this.toRad(lat2)) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
        
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        const distance = R * c;
        
        return distance;
    }

    calculateBearing(coords1, coords2) {
        const [lat1, lon1] = coords1;
        const [lat2, lon2] = coords2;
        
        const dLon = this.toRad(lon2 - lon1);
        
        const y = Math.sin(dLon) * Math.cos(this.toRad(lat2));
        const x = Math.cos(this.toRad(lat1)) * Math.sin(this.toRad(lat2)) -
                Math.sin(this.toRad(lat1)) * Math.cos(this.toRad(lat2)) * Math.cos(dLon);
        
        let bearing = Math.atan2(y, x);
        bearing = this.toDeg(bearing);
        bearing = (bearing + 360) % 360;
        
        return this.bearingToDirection(bearing);
    }

    toRad(degrees) {
        return degrees * (Math.PI / 180);
    }

    toDeg(radians) {
        return radians * (180 / Math.PI);
    }

    bearingToDirection(bearing) {
        const directions = ['North', 'North-East', 'East', 'South-East', 'South', 'South-West', 'West', 'North-West'];
        const index = Math.round(bearing / 45) % 8;
        return directions[index];
    }

    displayNavigationInfo(distance, bearing, destinationName) {
        const distanceElement = document.getElementById('distance-info');
        if (distanceElement) {
            distanceElement.innerHTML = `
                <i class="fas fa-road"></i>
                <span>${distance.toFixed(1)}km ${bearing} to ${destinationName}</span>
            `;
        }
    }

    startNavigation(destination) {
        this.destination = destination;
        this.navigationActive = true;
        
        if (!this.isTracking) {
            this.startTracking();
        }
        
        this.updateNavigationInfo();
        
        // Speak navigation start
        if (window.voiceController && window.voiceEnabled) {
            window.voiceController.speakText(`Starting navigation to ${destination}. Follow the directions.`);
        }
    }

    stopNavigation() {
        this.navigationActive = false;
        this.destination = null;
        
        const distanceElement = document.getElementById('distance-info');
        if (distanceElement) {
            distanceElement.innerHTML = `
                <i class="fas fa-road"></i>
                <span>- km to destination</span>
            `;
        }
    }

    updateGPSUI(active) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            if (active) {
                statusElement.innerHTML = '<i class="fas fa-satellite"></i> GPS Active';
                statusElement.style.background = 'var(--success-color)';
            } else {
                statusElement.innerHTML = '<i class="fas fa-wifi"></i> Online';
                statusElement.style.background = 'rgba(255,255,255,0.2)';
            }
        }
    }

    showGPSError(message) {
        // Show error in chat or as notification
        if (window.tourGuideApp) {
            window.tourGuideApp.addMessage(`GPS Error: ${message}`, 'bot');
        }
        
        // Show notification
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? 'var(--error-color)' : 'var(--primary-color)'};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            max-width: 300px;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    // Get nearby points of interest
    async getNearbyPOI(category = 'all', radius = 5) {
        if (!this.currentPosition) return [];
        
        // This would typically call a maps API
        // For demo, return simulated data
        return this.simulateNearbyPOI(category, radius);
    }

    simulateNearbyPOI(category, radius) {
        const pois = [
            {
                name: 'Central Park',
                type: 'park',
                distance: 0.5,
                bearing: 'North'
            },
            {
                name: 'Local Museum',
                type: 'museum',
                distance: 1.2,
                bearing: 'East'
            },
            {
                name: 'Shopping Mall',
                type: 'shopping',
                distance: 0.8,
                bearing: 'South'
            },
            {
                name: 'Restaurant Row',
                type: 'restaurant',
                distance: 0.3,
                bearing: 'West'
            }
        ];
        
        return pois.filter(poi => 
            category === 'all' || poi.type === category
        ).filter(poi => poi.distance <= radius);
    }
}

// Initialize GPS when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.gpsController = new GPSController();
    // Start GPS tracking automatically
    setTimeout(() => {
        window.gpsController.initializeGPS();
    }, 1000);
});
