import { MapContainer, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

function App() {
  return (
    <div style={{ padding: '20px' }}>
      <h1>Gator PathFinders</h1>

      <p>Choose a starting point and destination to plan your route.</p>

      <MapContainer //creates the map
        center={[29.6516, -82.3248]}
        zoom={13}
        style={{ height: '500px', width: '100%' }}
      >
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
      </MapContainer>
    </div>
  )
}

export default App