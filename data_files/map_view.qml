import QtQuick 2.15
import QtQuick.Window 2.15
import QtLocation 5.8
import QtPositioning 5.11

Window {
Map {
    id: map
    zoomLevel: (maximumZoomLevel - minimumZoomLevel)/2
    center {
        // The Qt Company in Oslo
        latitude: 59.9485
        longitude: 10.7686
    }
}
}