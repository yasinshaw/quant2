import { StrategyParameter } from '@/lib/api/strategies';
import { ImportRow } from './jsonParser';

export interface ValidationError {
  parameter: string;
  message: string;
  severity: 'error' | 'warning';
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
  parsedParameters: Record<string, any>;
}

/**
 * Validate imported parameters against strategy parameter definitions
 *
 * @param strict - If false, range violations become warnings instead of errors (for import)
 */
export function validateParameters(
  importRow: ImportRow,
  strategyParams: Record<string, StrategyParameter>,
  strict = true  // Default to strict mode, import uses false
): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];
  const parsedParameters: Record<string, any> = {};

  // Check for missing required parameters
  for (const [paramName, paramDef] of Object.entries(strategyParams)) {
    // Skip metadata keys (prefixed with _) - not actual strategy parameters
    if (paramName.startsWith('_')) continue;
    // Only consider it missing if:
    // 1. It's explicitly marked as required (or required is undefined/true)
    // 2. It's not in the imported data
    // 3. It doesn't have a default value
    const isRequired = paramDef.required !== false;
    const hasDefault = paramDef.default !== undefined;
    const isInImport = paramName in importRow.parameters;

    if (isRequired && !isInImport && !hasDefault) {
      errors.push({
        parameter: paramName,
        message: 'Missing required parameter (no default value)',
        severity: 'error',
      });
      continue;
    }

    // If parameter is not in imported data but has default, use default value
    if (!isInImport && hasDefault) {
      parsedParameters[paramName] = paramDef.default;
      continue;
    }

    if (isInImport) {
      const value = importRow.parameters[paramName];

      // Parse and validate value based on type
      const validation = validateParameterValue(paramName, value, paramDef, !strict);
      if (validation.valid) {
        parsedParameters[paramName] = validation.parsedValue;
      } else {
        if (validation.severity === 'error') {
          errors.push({
            parameter: paramName,
            message: validation.message || 'Validation error',
            severity: 'error',
          });
        } else {
          warnings.push({
            parameter: paramName,
            message: validation.message || 'Validation warning',
            severity: 'warning',
          });
          parsedParameters[paramName] = validation.parsedValue;
        }
      }
    }
  }

  // Check for unknown parameters
  for (const paramName of Object.keys(importRow.parameters)) {
    if (!(paramName in strategyParams)) {
      warnings.push({
        parameter: paramName,
        message: 'Unknown parameter (not defined in strategy)',
        severity: 'warning',
      });
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    parsedParameters,
  };
}

function validateParameterValue(
  _paramName: string,
  value: string | number,
  paramDef: StrategyParameter,
  lenient = false  // If true, range violations become warnings
): { valid: boolean; parsedValue: any; message?: string; severity?: 'error' | 'warning' } {
  let parsedValue: any = value;

  // Type conversion and validation
  switch (paramDef.type) {
    case 'int':
      parsedValue = typeof value === 'number' ? value : parseInt(String(value));
      if (isNaN(parsedValue)) {
        return {
          valid: false,
          parsedValue: paramDef.default,
          message: 'Invalid integer value',
          severity: 'error',
        };
      }
      break;

    case 'float':
      parsedValue = typeof value === 'number' ? value : parseFloat(String(value));
      if (isNaN(parsedValue)) {
        return {
          valid: false,
          parsedValue: paramDef.default,
          message: 'Invalid float value',
          severity: 'error',
        };
      }
      break;

    case 'bool':
      if (typeof value === 'boolean') {
        parsedValue = value;
      } else {
        const strValue = String(value).toLowerCase().trim();
        if (strValue === 'true' || strValue === '1' || strValue === 'yes') {
          parsedValue = true;
        } else if (strValue === 'false' || strValue === '0' || strValue === 'no') {
          parsedValue = false;
        } else {
          return {
            valid: false,
            parsedValue: paramDef.default,
            message: `Invalid boolean value: "${value}"`,
            severity: 'error',
          };
        }
      }
      break;

    case 'str':
      parsedValue = String(value);
      break;

    default:
      parsedValue = value;
  }

  // Range validation
  if (paramDef.min !== undefined && typeof parsedValue === 'number') {
    if (parsedValue < paramDef.min) {
      if (lenient) {
        // In lenient mode, range violations are warnings but still allow the value
        // We'll handle this separately after validation
      } else {
        return {
          valid: false,
          parsedValue,
          message: `Value ${parsedValue} is below minimum ${paramDef.min}`,
          severity: 'error',
        };
      }
    }
  }

  if (paramDef.max !== undefined && typeof parsedValue === 'number') {
    if (parsedValue > paramDef.max) {
      if (lenient) {
        // In lenient mode, range violations are warnings but still allow the value
        // We'll handle this separately after validation
      } else {
        return {
          valid: false,
          parsedValue,
          message: `Value ${parsedValue} exceeds maximum ${paramDef.max}`,
          severity: 'error',
        };
      }
    }
  }

  // Choices validation (always strict - invalid choices don't make sense)
  if (paramDef.choices && paramDef.choices.length > 0) {
    if (!paramDef.choices.includes(parsedValue)) {
      return {
        valid: false,
        parsedValue,
        message: `Value "${parsedValue}" is not in allowed choices: ${paramDef.choices.join(', ')}`,
        severity: 'error',
      };
    }
  }

  // In lenient mode, check for range violations and return warning if found
  if (lenient) {
    if (paramDef.min !== undefined && typeof parsedValue === 'number' && parsedValue < paramDef.min) {
      return {
        valid: true,  // Still valid, just with a warning
        parsedValue,
        message: `Value ${parsedValue} is below minimum ${paramDef.min}`,
        severity: 'warning',
      };
    }
    if (paramDef.max !== undefined && typeof parsedValue === 'number' && parsedValue > paramDef.max) {
      return {
        valid: true,  // Still valid, just with a warning
        parsedValue,
        message: `Value ${parsedValue} exceeds maximum ${paramDef.max}`,
        severity: 'warning',
      };
    }
  }

  return { valid: true, parsedValue };
}

/**
 * Format validation error/warning for display
 */
export function formatValidationMessage(validation: ValidationResult): string {
  if (validation.valid && validation.warnings.length === 0) {
    return 'All parameters validated successfully!';
  }

  const parts: string[] = [];

  if (validation.errors.length > 0) {
    parts.push(`Errors:\n${validation.errors.map(e => `  • ${e.parameter}: ${e.message}`).join('\n')}`);
  }

  if (validation.warnings.length > 0) {
    parts.push(`Warnings:\n${validation.warnings.map(w => `  • ${w.parameter}: ${w.message}`).join('\n')}`);
  }

  return parts.join('\n\n');
}
