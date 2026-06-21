interface ModelSelectorProps {
  model: string;
  temperature: number;
  onModelChange: (model: string) => void;
  onTempChange: (temp: number) => void;
}

const MODELS = [
  'Automatic Fallback',
  'DeepSeek Chat',
  'DeepSeek R1',
  'Gemini 2.5 Flash',
  'Gemini 1.5 Flash',
  'Gemini 1.5 Pro',
  'Llama 3.3 70B (Groq)',
  'Llama 3.1 8B (Groq)',
];

export function ModelSelector({
  model,
  temperature,
  onModelChange,
  onTempChange,
}: ModelSelectorProps) {
  return (
    <div
      className="p-4 rounded-lg space-y-4"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
      }}
    >
      <h3
        className="text-xs font-semibold uppercase tracking-wider"
        style={{ color: 'var(--text-secondary)' }}
      >
        Run Settings
      </h3>

      {/* Model Selector */}
      <div>
        <label
          className="block text-xs mb-1.5 font-medium"
          style={{ color: 'var(--text-secondary)' }}
        >
          Model
        </label>
        <select
          value={model}
          onChange={(e) => onModelChange(e.target.value)}
          className="w-full px-3 py-2 rounded-lg text-sm outline-none transition-colors"
          style={{
            backgroundColor: 'var(--bg-primary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
          }}
        >
          {MODELS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      {/* Temperature Slider */}
      <div>
        <label
          className="block text-xs mb-1.5 font-medium"
          style={{ color: 'var(--text-secondary)' }}
        >
          Temperature: {temperature.toFixed(1)}
        </label>
        <input
          type="range"
          min={0}
          max={2}
          step={0.1}
          value={temperature}
          onChange={(e) => onTempChange(parseFloat(e.target.value))}
          className="w-full accent-blue-500"
        />
        <div
          className="flex justify-between text-xs mt-1"
          style={{ color: 'var(--text-secondary)' }}
        >
          <span>Precise</span>
          <span>Creative</span>
        </div>
      </div>
    </div>
  );
}
