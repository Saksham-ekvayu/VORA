/* eslint-disable react/prop-types */
import { GeographicPicker } from "@/components/custom/GeographicPicker";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

/**
 * AddressFields Component - Standardized input layout for GeographicPicker address inputs.
 *
 * @param {string} prefix - "permanent" | "temporary"
 * @param {string} countryValue - Currently selected country name
 * @param {string} stateValue - Currently selected state name
 * @param {string} cityValue - Currently selected city name
 * @param {string} localityValue - Locality input value
 * @param {string} countryCode - Country ISO code for filtering states
 * @param {string} stateCode - State ISO code for filtering cities
 * @param {Function} onCountrySelect - Callback when country is picked
 * @param {Function} onStateSelect - Callback when state is picked
 * @param {Function} onCitySelect - Callback when city is picked
 * @param {Function} onLocalityChange - Callback when locality text changes
 * @param {boolean} disabled - Is picker interaction disabled
 */
export default function AddressFields({
  prefix,
  countryValue,
  stateValue,
  cityValue,
  localityValue,
  countryCode,
  stateCode,
  onCountrySelect,
  onStateSelect,
  onCitySelect,
  onLocalityChange,
  disabled = false,
}) {
  const isRequired = !disabled;

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Country */}
      <div className="space-y-1.5">
        <Label htmlFor={`${prefix}-country`}>
          Country{" "}
          {isRequired && <span className="required text-red-500">*</span>}
        </Label>
        <GeographicPicker
          type="country"
          value={countryValue}
          onSelect={onCountrySelect}
          placeholder="Country"
          disabled={disabled}
        />
      </div>

      {/* State */}
      <div className="space-y-1.5">
        <Label htmlFor={`${prefix}-state`}>
          State {isRequired && <span className="required text-red-500">*</span>}
        </Label>
        <GeographicPicker
          type="state"
          countryCode={countryCode}
          value={stateValue}
          onSelect={onStateSelect}
          placeholder={countryCode ? "State" : "Select Country"}
          disabled={disabled || !countryCode}
        />
      </div>

      {/* City */}
      <div className="space-y-1.5">
        <Label htmlFor={`${prefix}-city`}>
          City {isRequired && <span className="required text-red-500">*</span>}
        </Label>
        <GeographicPicker
          type="city"
          countryCode={countryCode}
          stateCode={stateCode}
          value={cityValue}
          onSelect={onCitySelect}
          placeholder={stateCode ? "City" : "Select State"}
          disabled={disabled || !stateCode}
        />
      </div>

      {/* Locality */}
      <div className="space-y-1.5">
        <Label htmlFor={`${prefix}-locality`}>
          Locality / Sector{" "}
          {isRequired && <span className="required text-red-500">*</span>}
        </Label>
        <Input
          id={`${prefix}-locality`}
          type="text"
          value={localityValue}
          onChange={(e) => onLocalityChange(e.target.value)}
          placeholder="Specific area"
          required={isRequired}
          disabled={disabled}
          className={disabled ? "bg-muted/50 cursor-not-allowed" : ""}
        />
      </div>
    </div>
  );
}
