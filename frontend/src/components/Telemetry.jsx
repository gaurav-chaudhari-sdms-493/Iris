import React from 'react';
import AcRemote from './AcRemote';
import Switchboard from './Switchboard';
import SystemLog from './SystemLog';

export default function Telemetry({ telemetry, onAcChange, onToggleSwitch }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
      
      {/* LEFT SIDE BLOCK (5 Columns): AC Broadlink IR Controller (Top) & Live System Event Log (Bottom) */}
      <div className="lg:col-span-5 flex flex-col gap-5 justify-between">
        <AcRemote telemetry={telemetry} onAcChange={onAcChange} />
        <SystemLog telemetry={telemetry} />
      </div>

      {/* RIGHT SIDE BLOCK (7 Columns): Physical 12-Gang Switchboard */}
      <div className="lg:col-span-7 flex flex-col justify-stretch">
        <Switchboard 
          relays={telemetry?.relays} 
          tvState={telemetry?.tv_state} 
          onToggleSwitch={onToggleSwitch} 
        />
      </div>

    </div>
  );
}
