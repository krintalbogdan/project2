import { useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip, Polyline, useMapEvents,} from 'react-leaflet'
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

type CoordinatePair = [number, number]

// Backend format: [row count, column count, ...grid coordinates].
type GridResult = [number, number, ...CoordinatePair[]]

function gridToLatLngs(
  result: GridResult,
  start: CoordinatePair,
  end: CoordinatePair,
): CoordinatePair[] {
  const [rows, cols, ...path] = result

  if (rows <= 0 || cols <= 0 || path.length === 0) {
    return []
  }

  // Find the geographic box between the selected points.
  const minLat = Math.min(start[0], end[0])
  const maxLat = Math.max(start[0], end[0])
  const minLng = Math.min(start[1], end[1])
  const maxLng = Math.max(start[1], end[1])

  // Estimate the geographic size of each grid cell.
  const latStep = (maxLat - minLat) / rows
  const lngStep = (maxLng - minLng) / cols

  // Estimate the center of the north-west cell.
  const lat0 = maxLat - latStep / 2
  const lng0 = minLng + lngStep / 2

  // Convert each [column, row] into [latitude, longitude].
  const latlngs: CoordinatePair[] = path.map(([col, row]) => [
    lat0 - row * latStep,
    lng0 + col * lngStep,
  ])

  // Connect the route ends to the exact selected locations.
  // A single-cell path needs both endpoints added explicitly.
  if (latlngs.length === 1) {
    return [start, end]
  }

  latlngs[0] = start
  latlngs[latlngs.length - 1] = end

  return latlngs
}

//the expected response from /process_query.
type RouteResult = {
  status: string
  path: GridResult
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

  //store the converted route points. An empty array means no line yet.
  const [route, setRoute] = useState<CoordinatePair[]>([])

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

async function findRoute() {
  if (!start || !end || loading) {
    return
  }

  setLoading(true)
  setError('')
  setRoute([])
  setApiMessage('Creating route request...')

  try {
    // First, ask the backend to create a pathfinding job.
    const response = await fetch(
      'http://127.0.0.1:8000/api/clone/create',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          from_coord: [start.lat, start.lng],
          to_coord: [end.lat, end.lng],
          algorithm,
        }),
      },
    )

    if (!response.ok) {
      throw new Error(`Creating job failed: HTTP ${response.status}`)
    }

    const job: { id: number } = await response.json()

    //check progress every two seconds, up to 60 times.
    //"await" lets the page stay responsive while we wait.
    for (let attempt = 0; attempt < 60; attempt++) {
      setApiMessage(`Calculating route - job ${job.id}...`)

      await new Promise((resolve) => setTimeout(resolve, 2000))

      const queryResponse = await fetch(
        'http://127.0.0.1:8000/api/clone/process_query',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ id: job.id }),
        },
      )

      if (!queryResponse.ok) {
        throw new Error(
          `Checking route failed: HTTP ${queryResponse.status}`,
        )
      }

      const result: RouteResult = await queryResponse.json()

      if (result.status === 'complete') {
        if (!result.path || result.path.length < 2) {
          throw new Error('The backend returned no drawable route.')
        }

        //convert the grid coordinates using tomas's function.
        setRoute(
          gridToLatLngs(
            result.path,
           [start.lat, start.lng],
            [end.lat, end.lng],
          ),
        )
        setApiMessage('Route received. Check the blue line on the map.')
        return
      }

      if (result.status === 'failed') {
        throw new Error('The backend could not calculate this route.')
      }
    }
  } catch (error) {
    setError(
      error instanceof Error ? error.message : 'Request failed',
    )
    setApiMessage('')
  } finally {
    //allow another request after completion or an error.
    setLoading(false)
  }
}

  function resetPoints() {
    setStart(null)
    setEnd(null)
    setRoute([]) //remove the previous route.
    setError('')
    setApiMessage('')
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

      <button type="button" onClick={resetPoints} disabled={loading}>
        Reset points
      </button>

      {/* Let the user choose which algorithm to run in a dropdown menu. */}
      <p>
        <label htmlFor="algorithm">Algorithm: </label>

        <select
          id="algorithm"
          value={algorithm}
          disabled={loading}
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

        {/* Connect the converted route points with a blue line. */}
        {route.length > 1 && (
         <Polyline
           positions={route}
            pathOptions={{ color: 'blue', weight: 5 }}
         />
        )}

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