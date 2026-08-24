interface TimeSliderProps {
  value: number;
  onChange: (value: number) => void;
}

const LABELS = ["Today", "+3d", "+7d"];

export default function TimeSlider({ value, onChange }: TimeSliderProps) {
  return (
    <div className="time-slider">
      {LABELS.map((label, i) => (
        <button
          key={label}
          className={`time-btn${i === value ? " active" : ""}`}
          onClick={() => onChange(i)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
