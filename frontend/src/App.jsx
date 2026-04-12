import React, { useState, useEffect } from 'react';
import axios from 'axios';
import TimelineChart from './components/TimelineChart';
import OrgChart from './components/OrgChart';
import './App.css';

const API_BASE = "http://localhost:8000/api";

function App() {
  const [currentDate, setCurrentDate] = useState('2024-01-01');
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchSnapshot = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`${API_BASE}/snapshot?date=${currentDate}`);
        setSnapshot(res.data);
      } catch (e) {
        console.error("Failed to fetch snapshot", e);
      }
      setLoading(false);
    };

    fetchSnapshot();
  }, [currentDate]);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Marsad Al-Idara</h1>
        <div className="search-bar">
          <input type="text" placeholder="Search persons, institutions, decrees..." />
        </div>
      </header>

      <main className="app-main">
        <section className="timeline-section">
          <TimelineChart 
            events={[]} 
            currentDate={currentDate} 
            onScrub={setCurrentDate} 
          />
        </section>

        <section className="view-section">
          <div className="view-controls">
             <h2>Administration Explorer</h2>
             <span className="current-date-display">Date: {currentDate}</span>
          </div>
          
          <div className="chart-container">
            {loading ? (
              <div className="loader">Updating administration map...</div>
            ) : (
              <OrgChart data={snapshot} />
            )}
          </div>
        </section>
      </main>

      <aside className="profile-drawer">
         {/* Drawer for details when a node is clicked */}
         <div className="drawer-placeholder">
           <p>Click an institution or person to see details</p>
         </div>
      </aside>
    </div>
  );
}

export default App;
