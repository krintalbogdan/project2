import { useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMapEvents,} from 'react-leaflet'
import { latLng } from 'leaflet' //latLng lets us calculate distances between coordinates
import 'leaflet/dist/leaflet.css'



const GAINESVILLE_FL = [29.6516, -82.3248]; // center of cell (0, 0)
const CELL_SIZE_M = 30;                     // meters between cell centers
const METERS_PER_DEG_LAT = 111320;

const LAT_STEP = CELL_SIZE_M / METERS_PER_DEG_LAT;
const LNG_STEP = CELL_SIZE_M /
  (METERS_PER_DEG_LAT * Math.cos(GAINESVILLE_FL[0] * Math.PI / 180));

// path: [[col, row], ...] as returned by execute_astar

type MapPoint = {
  lat: number
  lng: number
}

type MapClicksProps = {//this prop is information passed into React
  onSelect: (point: MapPoint) => void
}

function MapClicks({ onSelect }: MapClicksProps) {
  useMapEvents({
    click(event) {
      //event.latlng contains the location that was clicked.
      //wrap() keeps longitude within the standard range if the user drags across repeated copies of the world.
      const point = event.latlng.wrap()
      onSelect({ lat: point.lat, lng: point.lng })//pass coordinates to function
    },
  })
  return null
}

function App() {
  const [start, setStart] = useState<MapPoint | null>(null)//MapPoint | null means "a location OR no selection yet.
  const [end, setEnd] = useState<MapPoint | null>(null)
  const [error, setError] = useState('')
  const [algorithm, setAlgorithm] = useState('astar')
  //show the backend's reply on the page.
  const [apiMessage, setApiMessage] = useState('')
  //track whether a request is running to prevent repeated clicks.
  const [loading, setLoading] = useState(false)

  function selectPoint(point: MapPoint) {//runs when mapclicks gives clicked location
    if (!start) {
      setStart(point)
      setError('')
      return
    }
    if (!end) {
      const meters = latLng(start.lat, start.lng).distanceTo(latLng(point.lat, point.lng), )//use distanceTo function to calculate distance

      if (meters > 2 * 1609.344) {//1609.344 is number of meters in 1 mile
        setError('Destination must be within 2 miles of the start. Try closer.')
        return
      }

      if (meters < 1) {//this is just to prevent accidently selecting the same location twice
        setError('Choose a destination at least 1 meter from the start.')
        return
      }

      setEnd(point)
      setError('')
    }

  }

function gridToLatLngs(result: Array<Array<number>>, start: Array<number>, end: Array<number>) {
  const [rows, cols, ...path] = result;
  if (path.length === 0) return [];

  // box around start and end
  const minLat = Math.min(start[0], end[0]), maxLat = Math.max(start[0], end[0]);
  const minLng = Math.min(start[1], end[1]), maxLng = Math.max(start[1], end[1]);

  // size of one cell in degrees
  const latStep = (maxLat - minLat) / rows;
  const lngStep = (maxLng - minLng) / cols;

  // center of cell (0, 0), the north-west cell
  const lat0 = maxLat - latStep / 2;
  const lng0 = minLng + lngStep / 2;

  const latlngs = path.map(([col, row]) => [
    lat0 - row * latStep,  // rows run south
    lng0 + col * lngStep,  // columns run east
  ]);

  // pin the ends to the exact points
  latlngs[0] = [start[0], start[1]];
  latlngs[latlngs.length - 1] = [end[0], end[1]];
  return latlngs;
}
 

  async function findRoute(){//this function hands task to be sent to backend
    if (!start || !end) {
      setError('Select both points first.')
      return
    }

    setLoading(true)
    setError('')
    setApiMessage('Sending request...')

    try{
      // fetch sends an HTTP request, and await waits for the response without freezing the page.
      const response = await fetch(
      'http://127.0.0.1:8000/api/clone/create',{
        method: 'POST',//standard syntax for HTTP request
        headers: {
          'Content-Type': 'application/json',
        },

        //JSON.stringify converts this object into JSON text.
        body: JSON.stringify({
          from_coord: [start.lat, start.lng],
          to_coord: [end.lat, end.lng],
          algorithm: algorithm,
        }),
      },
    )

    if (!response.ok) {
      throw new Error(`Backend returned HTTP ${response.status}`)
    }

    const job = await response.json()//should contain job ID
    setApiMessage(`Job created with ID: ${job.id}`)
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Request failed', )//this is to handle connection errors
      setApiMessage('')
    } finally {
      setLoading(false)
    }
  }

  function resetPoints() {
    setStart(null)
    setEnd(null)
    setError('')
  }//reset function for reset button

  //remember this format "condition ? valueIfTrue : valueIfFalse"
  const distanceMiles =//if start and end exists calculate teh distance in miles
    start && end ? latLng(start.lat, start.lng).distanceTo(latLng(end.lat, end.lng)) /1609.344
      : null

  return (
    <div style={{ padding: '20px' }}>
      <h1>Gator PathFinders</h1>

      {/* Change the instructions based on what is selected. */}
      <p>
        {!start
          ? 'Click the map to choose your starting point.'
          : !end
            ? 'Now click a destination within 2 miles.'
            : 'Both points selected. Click Reset to choose again.'}
      </p>

      <button type="button" onClick={resetPoints}>
        Reset points
      </button>

      {/* Let the user choose which algorithm to run in a dropdown menu. */}
      <p>
        <label htmlFor="algorithm">Algorithm: </label>

        <select
          id="algorithm"
          value={algorithm}
          onChange={(event) => setAlgorithm(event.target.value)}
        >
          <option value="astar">A*</option>
          <option value="dijkstra">Dijkstra</option>
        </select>
      </p>

      {/* Enable the button only when both points are selected. */}
      <button
        type="button"
        onClick={findRoute}
        disabled={!start || !end || loading}
      >
        {loading ? 'Sending...' : 'Find Route'}
      </button>

      {/* Display the API request result. */}
      <p role="status">{apiMessage}</p>

      {/* toFixed(5) displays a number with five decimal places. */}
      <p>
        <strong>Start: </strong>
        {start
          ? `${start.lat.toFixed(5)}, ${start.lng.toFixed(5)}`
          : 'Not selected'}
      </p>

      <p>
        <strong>Destination: </strong>
        {end
          ? `${end.lat.toFixed(5)}, ${end.lng.toFixed(5)}`
          : 'Not selected'}
      </p>

      {distanceMiles !== null && (
        <p>Straight-line distance: {distanceMiles.toFixed(2)} miles</p>
      )}

      {/* Show why a destination was rejected. */}
      {error && (
        <p role="alert" style={{ color: '#b91c1c' }}>
          {error}
        </p>
      )}

      {/* Start the map in Gainesville and give it a visible height. */}
      <MapContainer //creates the map
        center={[29.6516, -82.3248]}
        zoom={13}
        style={{ height: '500px', width: '100%' }}
      >
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {/* When the map is clicked, MapClicks calls selectPoint. */}
        <MapClicks onSelect={selectPoint} />

        {/* Show the green circle only after a start is selected. Learned syntax from researching on google*/}
        {start && (
          <CircleMarker
            center={start}
            radius={10}
            pathOptions={{ color: 'green', fillOpacity: 0.8 }}
          >
            <Tooltip permanent>Start</Tooltip>
          </CircleMarker>
        )}

        {/* Show the red circle only after a destination is selected. */}
        {end && (
          <CircleMarker
            center={end}
            radius={10}
            pathOptions={{ color: 'red', fillOpacity: 0.8 }}
          >
            <Tooltip permanent>Destination</Tooltip>
          </CircleMarker>
        )}


      </MapContainer>
    </div>
  )
}

export default App