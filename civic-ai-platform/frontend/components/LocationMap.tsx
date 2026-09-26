"use client";

import L from "leaflet";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";

export type LocationMarker = {
  id?: string;
  latitude: number;
  longitude: number;
  label: string;
  color?: string;
};

type LocationMapProps = {
  markers: LocationMarker[];
  className?: string;
  height?: number;
  activeMarkerId?: string | null;
  emptyMessage?: string;
  onMarkerClick?: (marker: LocationMarker) => void;
  onMapClick?: (latitude: number, longitude: number) => void;
  openPopupMarkerId?: string | null;
};

const DEFAULT_CENTER: [number, number] = [22.5726, 88.3639];

function MapViewport({ markers }: { markers: LocationMarker[] }) {
  const map = useMap();

  useEffect(() => {
    if (markers.length === 0) return;

    if (markers.length === 1) {
      map.setView([markers[0].latitude, markers[0].longitude], 15, {
        animate: true,
      });
      return;
    }

    map.fitBounds(
      markers.map((marker) => [marker.latitude, marker.longitude] as [number, number]),
      { padding: [24, 24], maxZoom: 15, animate: true },
    );
  }, [map, markers]);

  return null;
}

function MapClickHandler({
  onMapClick,
}: {
  onMapClick?: (latitude: number, longitude: number) => void;
}) {
  useMapEvents({
    click(event) {
      onMapClick?.(event.latlng.lat, event.latlng.lng);
    },
  });

  return null;
}

function CurrentLocationControl({
  onLocated,
}: {
  onLocated?: (latitude: number, longitude: number) => void;
}) {
  const map = useMap();
  const [locating, setLocating] = useState(false);
  const [position, setPosition] = useState<[number, number] | null>(null);
  const [error, setError] = useState("");

  function locate() {
    setError("");

    if (!navigator.geolocation) {
      setError("Location is not supported by this browser.");
      return;
    }

    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const nextPosition: [number, number] = [coords.latitude, coords.longitude];
        setPosition(nextPosition);
        map.flyTo(nextPosition, Math.max(map.getZoom(), 15), { duration: 1.2 });
        onLocated?.(coords.latitude, coords.longitude);
        setLocating(false);
      },
      (geolocationError) => {
        setError(
          geolocationError.code === geolocationError.PERMISSION_DENIED
            ? "Location permission was denied. Allow it in your browser settings and try again."
            : geolocationError.code === geolocationError.TIMEOUT
              ? "Could not find your location in time. Please try again."
              : "Could not get your location. Check your device settings and try again.",
        );
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 },
    );
  }

  return (
    <>
      {position && (
        <CircleMarker
          center={position}
          radius={8}
          pathOptions={{ color: "#ffffff", weight: 3, fillColor: "#2563eb", fillOpacity: 1 }}
        />
      )}
      <div className="absolute right-3 top-3 z-[1000] flex max-w-[calc(100%-1.5rem)] flex-col items-end gap-2">
        <button
          type="button"
          onClick={locate}
          disabled={locating}
          className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-700 shadow-md transition hover:bg-slate-50 disabled:cursor-wait disabled:opacity-70"
        >
          {locating ? "Finding location..." : "? Use my current location"}
        </button>
        {error && (
          <p role="alert" className="max-w-xs rounded-xl bg-white/95 px-3 py-2 text-right text-xs font-medium text-red-700 shadow-md">
            {error}
          </p>
        )}
      </div>
    </>
  );
}
function LocationMarkerView({
  marker,
  icon,
  openPopup,
  onMarkerClick,
}: {
  marker: LocationMarker;
  icon: L.DivIcon;
  openPopup: boolean;
  onMarkerClick?: (marker: LocationMarker) => void;
}) {
  const markerRef = useRef<L.Marker | null>(null);

  useEffect(() => {
    if (openPopup) markerRef.current?.openPopup();
  }, [openPopup]);

  return (
    <Marker
      ref={markerRef}
      position={[marker.latitude, marker.longitude]}
      icon={icon}
      eventHandlers={{ click: () => onMarkerClick?.(marker) }}
    >
      <Popup>{marker.label}</Popup>
    </Marker>
  );
}

export default function LocationMap({
  markers,
  className = "",
  height = 260,
  activeMarkerId = null,
  emptyMessage = "Search for a location to place a pin",
  onMarkerClick,
  onMapClick,
  openPopupMarkerId = null,
}: LocationMapProps) {
  const createMarkerIcon = useMemo(
    () => (active: boolean, color?: string) =>
      L.divIcon({
        className: "civic-map-marker",
        html: `<span style="display:block;width:${active ? 24 : 18}px;height:${active ? 24 : 18}px;border:3px solid white;border-radius:9999px;background:${active ? "#c45c46" : color ?? "#117d78"};box-shadow:0 2px 8px rgba(18,36,58,.35)"></span>`,
        iconSize: active ? [24, 24] : [18, 18],
        iconAnchor: active ? [12, 12] : [9, 9],
      }),
    [],
  );

  const initialCenter: [number, number] = markers[0]
    ? [markers[0].latitude, markers[0].longitude]
    : DEFAULT_CENTER;

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border border-slate-200 ${className}`}
      style={{ height }}
    >
      <MapContainer
        center={initialCenter}
        zoom={markers.length ? 15 : 11}
        scrollWheelZoom
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapClickHandler onMapClick={onMapClick} />
        <CurrentLocationControl onLocated={onMapClick} />
        <MapViewport markers={markers} />
        {markers.map((marker, index) => (
          <LocationMarkerView
            key={marker.id ?? `${marker.latitude}-${marker.longitude}-${index}`}
            marker={marker}
            icon={createMarkerIcon(marker.id === activeMarkerId, marker.color)}
            openPopup={marker.id === openPopupMarkerId}
            onMarkerClick={onMarkerClick}
          />
        ))}
      </MapContainer>
      {markers.length === 0 && (
        <div className="pointer-events-none absolute inset-x-0 bottom-3 mx-auto w-max rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-slate-500 shadow-sm">
          {emptyMessage}
        </div>
      )}
    </div>
  );
}
