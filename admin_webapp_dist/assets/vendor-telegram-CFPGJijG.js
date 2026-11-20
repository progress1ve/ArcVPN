import { r as reactExports } from './vendor-react-CZvSMMDv.js';

//#region src/storages/globalConfig/globalConfig.ts
const DEFAULT_CONFIG = {
	lang: void 0,
	message: void 0,
	abortEarly: void 0,
	abortPipeEarly: void 0
};
/**
* Returns the global configuration.
*
* @param config The config to merge.
*
* @returns The configuration.
*/
/* @__NO_SIDE_EFFECTS__ */
function getGlobalConfig(config$1) {
	return DEFAULT_CONFIG;
}

//#endregion
//#region src/storages/globalMessage/globalMessage.ts
let store$3;
/**
* Returns a global error message.
*
* @param lang The language of the message.
*
* @returns The error message.
*/
/* @__NO_SIDE_EFFECTS__ */
function getGlobalMessage(lang) {
	return store$3?.get(lang);
}

//#endregion
//#region src/storages/schemaMessage/schemaMessage.ts
let store$2;
/**
* Returns a schema error message.
*
* @param lang The language of the message.
*
* @returns The error message.
*/
/* @__NO_SIDE_EFFECTS__ */
function getSchemaMessage(lang) {
	return store$2?.get(lang);
}

//#endregion
//#region src/storages/specificMessage/specificMessage.ts
let store$1;
/**
* Returns a specific error message.
*
* @param reference The identifier reference.
* @param lang The language of the message.
*
* @returns The error message.
*/
/* @__NO_SIDE_EFFECTS__ */
function getSpecificMessage(reference, lang) {
	return store$1?.get(reference)?.get(lang);
}

//#endregion
//#region src/utils/_stringify/_stringify.ts
/**
* Stringifies an unknown input to a literal or type string.
*
* @param input The unknown input.
*
* @returns A literal or type string.
*
* @internal
*/
/* @__NO_SIDE_EFFECTS__ */
function _stringify(input) {
	const type = typeof input;
	if (type === "string") return `"${input}"`;
	if (type === "number" || type === "bigint" || type === "boolean") return `${input}`;
	if (type === "object" || type === "function") return (input && Object.getPrototypeOf(input)?.constructor?.name) ?? "null";
	return type;
}

//#endregion
//#region src/utils/_addIssue/_addIssue.ts
/**
* Adds an issue to the dataset.
*
* @param context The issue context.
* @param label The issue label.
* @param dataset The input dataset.
* @param config The configuration.
* @param other The optional props.
*
* @internal
*/
function _addIssue(context, label, dataset, config$1, other) {
	const input = other && "input" in other ? other.input : dataset.value;
	const expected = other?.expected ?? context.expects ?? null;
	const received = other?.received ?? /* @__PURE__ */ _stringify(input);
	const issue = {
		kind: context.kind,
		type: context.type,
		input,
		expected,
		received,
		message: `Invalid ${label}: ${expected ? `Expected ${expected} but r` : "R"}eceived ${received}`,
		requirement: context.requirement,
		path: other?.path,
		issues: other?.issues,
		lang: config$1.lang,
		abortEarly: config$1.abortEarly,
		abortPipeEarly: config$1.abortPipeEarly
	};
	const isSchema = context.kind === "schema";
	const message$1 = other?.message ?? context.message ?? /* @__PURE__ */ getSpecificMessage(context.reference, issue.lang) ?? (isSchema ? /* @__PURE__ */ getSchemaMessage(issue.lang) : null) ?? config$1.message ?? /* @__PURE__ */ getGlobalMessage(issue.lang);
	if (message$1 !== void 0) issue.message = typeof message$1 === "function" ? message$1(issue) : message$1;
	if (isSchema) dataset.typed = false;
	if (dataset.issues) dataset.issues.push(issue);
	else dataset.issues = [issue];
}

//#endregion
//#region src/utils/_getStandardProps/_getStandardProps.ts
const _standardCache = /* @__PURE__ */ new WeakMap();
/**
* Returns the Standard Schema properties.
*
* @param context The schema context.
*
* @returns The Standard Schema properties.
*/
/* @__NO_SIDE_EFFECTS__ */
function _getStandardProps(context) {
	let cached = _standardCache.get(context);
	if (!cached) {
		cached = {
			version: 1,
			vendor: "valibot",
			validate(value$1) {
				return context["~run"]({ value: value$1 }, /* @__PURE__ */ getGlobalConfig());
			}
		};
		_standardCache.set(context, cached);
	}
	return cached;
}

//#endregion
//#region src/utils/_isValidObjectKey/_isValidObjectKey.ts
/**
* Disallows inherited object properties and prevents object prototype
* pollution by disallowing certain keys.
*
* @param object The object to check.
* @param key The key to check.
*
* @returns Whether the key is allowed.
*
* @internal
*/
/* @__NO_SIDE_EFFECTS__ */
function _isValidObjectKey(object$1, key) {
	return Object.prototype.hasOwnProperty.call(object$1, key) && key !== "__proto__" && key !== "prototype" && key !== "constructor";
}

//#endregion
//#region src/utils/_joinExpects/_joinExpects.ts
/**
* Joins multiple `expects` values with the given separator.
*
* @param values The `expects` values.
* @param separator The separator.
*
* @returns The joined `expects` property.
*
* @internal
*/
/* @__NO_SIDE_EFFECTS__ */
function _joinExpects(values$1, separator) {
	const list = [...new Set(values$1)];
	if (list.length > 1) return `(${list.join(` ${separator} `)})`;
	return list[0] ?? "never";
}

//#endregion
//#region src/utils/ValiError/ValiError.ts
/**
* A Valibot error with useful information.
*/
var ValiError = class extends Error {
	/**
	* Creates a Valibot error with useful information.
	*
	* @param issues The error issues.
	*/
	constructor(issues) {
		super(issues[0].message);
		this.name = "ValiError";
		this.issues = issues;
	}
};

//#endregion
//#region src/actions/transform/transform.ts
/**
* Creates a custom transformation action.
*
* @param operation The transformation operation.
*
* @returns A transform action.
*/
/* @__NO_SIDE_EFFECTS__ */
function transform(operation) {
	return {
		kind: "transformation",
		type: "transform",
		reference: transform,
		async: false,
		operation,
		"~run"(dataset) {
			dataset.value = this.operation(dataset.value);
			return dataset;
		}
	};
}

//#endregion
//#region src/const.ts
const ABORT_EARLY_CONFIG = { abortEarly: true };

//#endregion
//#region src/methods/getFallback/getFallback.ts
/**
* Returns the fallback value of the schema.
*
* @param schema The schema to get it from.
* @param dataset The output dataset if available.
* @param config The config if available.
*
* @returns The fallback value.
*/
/* @__NO_SIDE_EFFECTS__ */
function getFallback(schema, dataset, config$1) {
	return typeof schema.fallback === "function" ? schema.fallback(dataset, config$1) : schema.fallback;
}

//#endregion
//#region src/methods/getDefault/getDefault.ts
/**
* Returns the default value of the schema.
*
* @param schema The schema to get it from.
* @param dataset The input dataset if available.
* @param config The config if available.
*
* @returns The default value.
*/
/* @__NO_SIDE_EFFECTS__ */
function getDefault(schema, dataset, config$1) {
	return typeof schema.default === "function" ? schema.default(dataset, config$1) : schema.default;
}

//#endregion
//#region src/methods/is/is.ts
/**
* Checks if the input matches the schema. By using a type predicate, this
* function can be used as a type guard.
*
* @param schema The schema to be used.
* @param input The input to be tested.
*
* @returns Whether the input matches the schema.
*/
/* @__NO_SIDE_EFFECTS__ */
function is$1(schema, input) {
	return !schema["~run"]({ value: input }, ABORT_EARLY_CONFIG).issues;
}

//#endregion
//#region src/schemas/array/array.ts
/* @__NO_SIDE_EFFECTS__ */
function array(item, message$1) {
	return {
		kind: "schema",
		type: "array",
		reference: array,
		expects: "Array",
		async: false,
		item,
		message: message$1,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			const input = dataset.value;
			if (Array.isArray(input)) {
				dataset.typed = true;
				dataset.value = [];
				for (let key = 0; key < input.length; key++) {
					const value$1 = input[key];
					const itemDataset = this.item["~run"]({ value: value$1 }, config$1);
					if (itemDataset.issues) {
						const pathItem = {
							type: "array",
							origin: "value",
							input,
							key,
							value: value$1
						};
						for (const issue of itemDataset.issues) {
							if (issue.path) issue.path.unshift(pathItem);
							else issue.path = [pathItem];
							dataset.issues?.push(issue);
						}
						if (!dataset.issues) dataset.issues = itemDataset.issues;
						if (config$1.abortEarly) {
							dataset.typed = false;
							break;
						}
					}
					if (!itemDataset.typed) dataset.typed = false;
					dataset.value.push(itemDataset.value);
				}
			} else _addIssue(this, "type", dataset, config$1);
			return dataset;
		}
	};
}

//#endregion
//#region src/schemas/boolean/boolean.ts
/* @__NO_SIDE_EFFECTS__ */
function boolean(message$1) {
	return {
		kind: "schema",
		type: "boolean",
		reference: boolean,
		expects: "boolean",
		async: false,
		message: message$1,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			if (typeof dataset.value === "boolean") dataset.typed = true;
			else _addIssue(this, "type", dataset, config$1);
			return dataset;
		}
	};
}

//#endregion
//#region src/schemas/date/date.ts
/* @__NO_SIDE_EFFECTS__ */
function date(message$1) {
	return {
		kind: "schema",
		type: "date",
		reference: date,
		expects: "Date",
		async: false,
		message: message$1,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			if (dataset.value instanceof Date) if (!isNaN(dataset.value)) dataset.typed = true;
			else _addIssue(this, "type", dataset, config$1, { received: "\"Invalid Date\"" });
			else _addIssue(this, "type", dataset, config$1);
			return dataset;
		}
	};
}

//#endregion
//#region src/schemas/function/function.ts
/* @__NO_SIDE_EFFECTS__ */
function function_(message$1) {
	return {
		kind: "schema",
		type: "function",
		reference: function_,
		expects: "Function",
		async: false,
		message: message$1,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			if (typeof dataset.value === "function") dataset.typed = true;
			else _addIssue(this, "type", dataset, config$1);
			return dataset;
		}
	};
}

//#endregion
//#region src/schemas/instance/instance.ts
/* @__NO_SIDE_EFFECTS__ */
function instance(class_, message$1) {
	return {
		kind: "schema",
		type: "instance",
		reference: instance,
		expects: class_.name,
		async: false,
		class: class_,
		message: message$1,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			if (dataset.value instanceof this.class) dataset.typed = true;
			else _addIssue(this, "type", dataset, config$1);
			return dataset;
		}
	};
}

//#endregion
//#region src/schemas/looseObject/looseObject.ts
/* @__NO_SIDE_EFFECTS__ */
function looseObject(entries$1, message$1) {
	return {
		kind: "schema",
		type: "loose_object",
		reference: looseObject,
		expects: "Object",
		async: false,
		entries: entries$1,
		message: message$1,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			const input = dataset.value;
			if (input && typeof input === "object") {
				dataset.typed = true;
				dataset.value = {};
				for (const key in this.entries) {
					const valueSchema = this.entries[key];
					if (key in input || (valueSchema.type === "exact_optional" || valueSchema.type === "optional" || valueSchema.type === "nullish") && valueSchema.default !== void 0) {
						const value$1 = key in input ? input[key] : /* @__PURE__ */ getDefault(valueSchema);
						const valueDataset = valueSchema["~run"]({ value: value$1 }, config$1);
						if (valueDataset.issues) {
							const pathItem = {
								type: "object",
								origin: "value",
								input,
								key,
								value: value$1
							};
							for (const issue of valueDataset.issues) {
								if (issue.path) issue.path.unshift(pathItem);
								else issue.path = [pathItem];
								dataset.issues?.push(issue);
							}
							if (!dataset.issues) dataset.issues = valueDataset.issues;
							if (config$1.abortEarly) {
								dataset.typed = false;
								break;
							}
						}
						if (!valueDataset.typed) dataset.typed = false;
						dataset.value[key] = valueDataset.value;
					} else if (valueSchema.fallback !== void 0) dataset.value[key] = /* @__PURE__ */ getFallback(valueSchema);
					else if (valueSchema.type !== "exact_optional" && valueSchema.type !== "optional" && valueSchema.type !== "nullish") {
						_addIssue(this, "key", dataset, config$1, {
							input: void 0,
							expected: `"${key}"`,
							path: [{
								type: "object",
								origin: "key",
								input,
								key,
								value: input[key]
							}]
						});
						if (config$1.abortEarly) break;
					}
				}
				if (!dataset.issues || !config$1.abortEarly) {
					for (const key in input) if (/* @__PURE__ */ _isValidObjectKey(input, key) && !(key in this.entries)) dataset.value[key] = input[key];
				}
			} else _addIssue(this, "type", dataset, config$1);
			return dataset;
		}
	};
}

//#endregion
//#region src/schemas/nullish/nullish.ts
/* @__NO_SIDE_EFFECTS__ */
function nullish(wrapped, default_) {
	return {
		kind: "schema",
		type: "nullish",
		reference: nullish,
		expects: `(${wrapped.expects} | null | undefined)`,
		async: false,
		wrapped,
		default: default_,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			if (dataset.value === null || dataset.value === void 0) {
				if (this.default !== void 0) dataset.value = /* @__PURE__ */ getDefault(this, dataset, config$1);
				if (dataset.value === null || dataset.value === void 0) {
					dataset.typed = true;
					return dataset;
				}
			}
			return this.wrapped["~run"](dataset, config$1);
		}
	};
}

//#endregion
//#region src/schemas/number/number.ts
/* @__NO_SIDE_EFFECTS__ */
function number(message$1) {
	return {
		kind: "schema",
		type: "number",
		reference: number,
		expects: "number",
		async: false,
		message: message$1,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			if (typeof dataset.value === "number" && !isNaN(dataset.value)) dataset.typed = true;
			else _addIssue(this, "type", dataset, config$1);
			return dataset;
		}
	};
}

//#endregion
//#region src/schemas/optional/optional.ts
/* @__NO_SIDE_EFFECTS__ */
function optional(wrapped, default_) {
	return {
		kind: "schema",
		type: "optional",
		reference: optional,
		expects: `(${wrapped.expects} | undefined)`,
		async: false,
		wrapped,
		default: default_,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			if (dataset.value === void 0) {
				if (this.default !== void 0) dataset.value = /* @__PURE__ */ getDefault(this, dataset, config$1);
				if (dataset.value === void 0) {
					dataset.typed = true;
					return dataset;
				}
			}
			return this.wrapped["~run"](dataset, config$1);
		}
	};
}

//#endregion
//#region src/schemas/record/record.ts
/* @__NO_SIDE_EFFECTS__ */
function record(key, value$1, message$1) {
	return {
		kind: "schema",
		type: "record",
		reference: record,
		expects: "Object",
		async: false,
		key,
		value: value$1,
		message: message$1,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			const input = dataset.value;
			if (input && typeof input === "object") {
				dataset.typed = true;
				dataset.value = {};
				for (const entryKey in input) if (/* @__PURE__ */ _isValidObjectKey(input, entryKey)) {
					const entryValue = input[entryKey];
					const keyDataset = this.key["~run"]({ value: entryKey }, config$1);
					if (keyDataset.issues) {
						const pathItem = {
							type: "object",
							origin: "key",
							input,
							key: entryKey,
							value: entryValue
						};
						for (const issue of keyDataset.issues) {
							issue.path = [pathItem];
							dataset.issues?.push(issue);
						}
						if (!dataset.issues) dataset.issues = keyDataset.issues;
						if (config$1.abortEarly) {
							dataset.typed = false;
							break;
						}
					}
					const valueDataset = this.value["~run"]({ value: entryValue }, config$1);
					if (valueDataset.issues) {
						const pathItem = {
							type: "object",
							origin: "value",
							input,
							key: entryKey,
							value: entryValue
						};
						for (const issue of valueDataset.issues) {
							if (issue.path) issue.path.unshift(pathItem);
							else issue.path = [pathItem];
							dataset.issues?.push(issue);
						}
						if (!dataset.issues) dataset.issues = valueDataset.issues;
						if (config$1.abortEarly) {
							dataset.typed = false;
							break;
						}
					}
					if (!keyDataset.typed || !valueDataset.typed) dataset.typed = false;
					if (keyDataset.typed) dataset.value[keyDataset.value] = valueDataset.value;
				}
			} else _addIssue(this, "type", dataset, config$1);
			return dataset;
		}
	};
}

//#endregion
//#region src/schemas/string/string.ts
/* @__NO_SIDE_EFFECTS__ */
function string(message$1) {
	return {
		kind: "schema",
		type: "string",
		reference: string,
		expects: "string",
		async: false,
		message: message$1,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			if (typeof dataset.value === "string") dataset.typed = true;
			else _addIssue(this, "type", dataset, config$1);
			return dataset;
		}
	};
}

//#endregion
//#region src/schemas/union/utils/_subIssues/_subIssues.ts
/**
* Returns the sub issues of the provided datasets for the union issue.
*
* @param datasets The datasets.
*
* @returns The sub issues.
*
* @internal
*/
/* @__NO_SIDE_EFFECTS__ */
function _subIssues(datasets) {
	let issues;
	if (datasets) for (const dataset of datasets) if (issues) for (const issue of dataset.issues) issues.push(issue);
	else issues = dataset.issues;
	return issues;
}

//#endregion
//#region src/schemas/union/union.ts
/* @__NO_SIDE_EFFECTS__ */
function union(options, message$1) {
	return {
		kind: "schema",
		type: "union",
		reference: union,
		expects: /* @__PURE__ */ _joinExpects(options.map((option) => option.expects), "|"),
		async: false,
		options,
		message: message$1,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			let validDataset;
			let typedDatasets;
			let untypedDatasets;
			for (const schema of this.options) {
				const optionDataset = schema["~run"]({ value: dataset.value }, config$1);
				if (optionDataset.typed) if (optionDataset.issues) if (typedDatasets) typedDatasets.push(optionDataset);
				else typedDatasets = [optionDataset];
				else {
					validDataset = optionDataset;
					break;
				}
				else if (untypedDatasets) untypedDatasets.push(optionDataset);
				else untypedDatasets = [optionDataset];
			}
			if (validDataset) return validDataset;
			if (typedDatasets) {
				if (typedDatasets.length === 1) return typedDatasets[0];
				_addIssue(this, "type", dataset, config$1, { issues: /* @__PURE__ */ _subIssues(typedDatasets) });
				dataset.typed = true;
			} else if (untypedDatasets?.length === 1) return untypedDatasets[0];
			else _addIssue(this, "type", dataset, config$1, { issues: /* @__PURE__ */ _subIssues(untypedDatasets) });
			return dataset;
		}
	};
}

//#endregion
//#region src/schemas/unknown/unknown.ts
/**
* Creates a unknown schema.
*
* @returns A unknown schema.
*/
/* @__NO_SIDE_EFFECTS__ */
function unknown() {
	return {
		kind: "schema",
		type: "unknown",
		reference: unknown,
		expects: "unknown",
		async: false,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset) {
			dataset.typed = true;
			return dataset;
		}
	};
}

//#endregion
//#region src/methods/parse/parse.ts
/**
* Parses an unknown input based on a schema.
*
* @param schema The schema to be used.
* @param input The input to be parsed.
* @param config The parse configuration.
*
* @returns The parsed input.
*/
function parse(schema, input, config$1) {
	const dataset = schema["~run"]({ value: input }, /* @__PURE__ */ getGlobalConfig());
	if (dataset.issues) throw new ValiError(dataset.issues);
	return dataset.value;
}

//#endregion
//#region src/methods/pipe/pipe.ts
/* @__NO_SIDE_EFFECTS__ */
function pipe(...pipe$1) {
	return {
		...pipe$1[0],
		pipe: pipe$1,
		get "~standard"() {
			return /* @__PURE__ */ _getStandardProps(this);
		},
		"~run"(dataset, config$1) {
			for (const item of pipe$1) if (item.kind !== "metadata") {
				if (dataset.issues && (item.kind === "schema" || item.kind === "transformation")) {
					dataset.typed = false;
					break;
				}
				if (!dataset.issues || !config$1.abortEarly && !config$1.abortPipeEarly) dataset = item["~run"](dataset, config$1);
			}
			return dataset;
		}
	};
}

var V$3 = Object.defineProperty;
var Y$2 = (r, t, e) => t in r ? V$3(r, t, { enumerable: true, configurable: true, writable: true, value: e }) : r[t] = e;
var y$3 = (r, t, e) => Y$2(r, typeof t != "symbol" ? t + "" : t, e);
var $$2 = Object.defineProperty, k$2 = (r, t, e) => t in r ? $$2(r, t, { enumerable: true, configurable: true, writable: true, value: e }) : r[t] = e, q$1 = (r, t, e) => k$2(r, t + "", e);
function z$3(r, t) {
  return (e) => e instanceof r && e.type === t;
}
function P(r, t) {
  t || (t = []);
  const e = Symbol(r);
  class c extends Error {
    constructor(...s) {
      const a = typeof t == "function" ? t(...s) : typeof t == "string" ? [t] : t || [];
      super(...a), q$1(this, "type", e), this.name = r;
    }
  }
  return Object.defineProperty(c, "name", { value: r }), [c, z$3(c, e)];
}
const [G$2, M$1] = P("CancelledError", "Promise was canceled"), [H$3] = P(
  "TimeoutError",
  (r, t) => [`Timeout reached: ${r}ms`, { cause: t }]
), B$2 = Symbol("Resolved");
function C$1(r) {
  return Array.isArray(r) && r[0] === B$2;
}
function J$2(r) {
  return [B$2, r];
}
function x$3(r, t) {
  return r.reject = t.reject, r.abort = t.abort, r;
}
let m$1 = class m extends Promise {
  constructor(e, c) {
    let o, s;
    super((a, i) => {
      let v, u;
      typeof e == "function" ? (v = e, u = c) : u = e;
      const d = [], j = (n) => (...h) => {
        const p = n(...h);
        return d.forEach((F) => F()), p;
      }, g = new AbortController(), { signal: l } = g;
      s = (n) => {
        !l.aborted && g.abort(n);
      };
      const b = () => l.reason, w = (n) => {
        const h = () => {
          n(b());
        };
        l.addEventListener("abort", h, true);
        const p = () => {
          l.removeEventListener("abort", h, true);
        };
        return d.push(p), p;
      }, D = j((n) => {
        a(n), s(J$2(n));
      });
      o = j((n) => {
        i(n), s(n);
      }), u || (u = {});
      const { abortSignal: f, rejectOnAbort: A = true } = u;
      if (f)
        if (f.aborted) {
          const { reason: n } = f;
          if (A)
            return o(n);
          s(n);
        } else {
          const n = () => {
            s(f.reason);
          };
          f.addEventListener("abort", n), d.push(() => {
            f.removeEventListener("abort", n);
          });
        }
      A && w(i);
      const { timeout: E } = u;
      if (E) {
        const n = setTimeout(() => {
          s(new H$3(E));
        }, E);
        d.push(() => {
          clearTimeout(n);
        });
      }
      const L = () => l.aborted, S = () => C$1(b()), T = () => {
        const n = b();
        return C$1(n) ? n[1] : void 0;
      };
      try {
        const n = v && v(D, o, {
          abortReason: b,
          abortSignal: l,
          isAborted: L,
          isResolved: S,
          onAborted: w,
          onResolved: (h) => w(() => {
            S() && h(T());
          }),
          resolved: T,
          throwIfAborted() {
            if (L())
              throw b();
          }
        });
        n instanceof Promise && n.catch(o);
      } catch (n) {
        o(n);
      }
    });
    /**
     * Aborts the promise execution using the specified reason.
     *
     * Not that this method doesn't reject the promise but notifies the executor using its context.
     * To perform the same operation but also reject the promise, use the `reject()` method.
     * @param reason - abort reason.
     * @see reject
     */
    y$3(this, "abort");
    /**
     * Rejects the initially created promise.
     *
     * This method not only aborts the signal passed to the executor, but also rejects the
     * promise itself calling all chained listeners.
     *
     * The reason passed to the method is being passed as-is to the executor's context.
     */
    y$3(this, "reject");
    this.abort = s, this.reject = o;
  }
  /**
   * Creates a new AbortablePromise instance using an executor, resolving the promise when a result
   * was returned.
   * @param fn - function returning promise result.
   * @param options - additional options.
   */
  static fn(e, c) {
    return new m(async (o, s, a) => {
      try {
        o(await e(a));
      } catch (i) {
        s(i);
      }
    }, c);
  }
  static resolve(e) {
    return this.fn(() => e);
  }
  /**
   * @see Promise.reject
   */
  static reject(e) {
    return new m((c, o) => {
      o(e);
    });
  }
  /**
   * Aborts the promise with the cancel error.
   */
  cancel() {
    this.abort(new G$2());
  }
  /**
   * @see Promise.catch
   */
  catch(e) {
    return this.then(void 0, e);
  }
  /**
   * @see Promise.finally
   */
  finally(e) {
    return x$3(super.finally(e), this);
  }
  /**
   * @see Promise.then
   */
  then(e, c) {
    return x$3(super.then(e, c), this);
  }
};
function I$3(r, t) {
  return r.resolve = t.resolve, r;
}
let R$2 = class R extends m$1 {
  constructor(e, c) {
    let o, s;
    typeof e == "function" ? (o = e, s = c) : s = e;
    let a;
    super((i, v, u) => {
      a = i, o && o(i, v, u);
    }, s);
    /**
     * Resolves the promise.
     */
    y$3(this, "resolve");
    this.resolve = a;
  }
  /**
   * Creates a new ManualPromise instance using an executor, resolving the promise when a result
   * was returned.
   * @param fn - function returning promise result.
   * @param options - additional options.
   */
  static fn(e, c) {
    return new R((o, s, a) => {
      try {
        Promise.resolve(e(a)).then(o, s);
      } catch (i) {
        s(i);
      }
    }, c);
  }
  static resolve(e) {
    return this.fn(() => e);
  }
  /**
   * @see Promise.reject
   */
  static reject(e) {
    return new R((c, o) => {
      o(e);
    });
  }
  /**
   * @see Promise.catch
   */
  catch(e) {
    return this.then(void 0, e);
  }
  /**
   * @see Promise.finally
   */
  finally(e) {
    return I$3(super.finally(e), this);
  }
  /**
   * @see Promise.then
   */
  then(e, c) {
    return I$3(super.then(e, c), this);
  }
};

function y$2(o) {
  return o.replace(/[A-Z]/g, (e) => `-${e.toLowerCase()}`);
}
function k$1(o) {
  return o.replace(/_([a-z])/g, (e, r) => `-${r.toLowerCase()}`);
}
function g$1(o) {
  return `tapps/${o}`;
}
function w$2(o, e) {
  sessionStorage.setItem(g$1(o), JSON.stringify(e));
}
function T$1(o) {
  const e = sessionStorage.getItem(g$1(o));
  try {
    return e ? JSON.parse(e) : void 0;
  } catch {
  }
}
function L$2(...o) {
  const e = o.flat(1);
  return [
    e.push.bind(e),
    () => {
      e.forEach((r) => {
        r();
      });
    }
  ];
}
// @__NO_SIDE_EFFECTS__
function O$2(o, e) {
  e || (e = {});
  const {
    textColor: r,
    bgColor: t,
    shouldLog: s
  } = e, c = s === void 0 ? true : s, d = typeof c == "boolean" ? () => c : c, u = (n, a, ...i) => {
    if (a || d()) {
      const l = "font-weight:bold;padding:0 5px;border-radius:100px", [b, m, p] = {
        log: ["#0089c3", "white", "INFO"],
        error: ["#ff0000F0", "white", "ERR"],
        warn: ["#D38E15", "white", "WARN"]
      }[n];
      console[n](
        `%c${p} ${Intl.DateTimeFormat("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          fractionalSecondDigits: 3,
          timeZone: "UTC"
        }).format(/* @__PURE__ */ new Date())}%c %c${o}`,
        `${l};background-color:${b};color:${m}`,
        "",
        `${l};${r ? `color:${r};` : ""}${t ? `background-color:${t}` : ""}`,
        ...i
      );
    }
  };
  return [
    ["log", "forceLog"],
    ["warn", "forceWarn"],
    ["error", "forceError"]
  ].reduce((n, [a, i]) => (n[a] = u.bind(void 0, a, false), n[i] = u.bind(void 0, a, true), n), {});
}

// @__NO_SIDE_EFFECTS__
function N$1(e) {
  return {
    lang: (e == null ? void 0 : e.lang) ?? (void 0 ),
    message: e == null ? void 0 : e.message,
    abortEarly: (e == null ? void 0 : e.abortEarly) ?? (void 0 ),
    abortPipeEarly: (e == null ? void 0 : e.abortPipeEarly) ?? (void 0 )
  };
}
// @__NO_SIDE_EFFECTS__
function Z$2(e) {
  return void 0 ;
}
// @__NO_SIDE_EFFECTS__
function ee$2(e) {
  return void 0 ;
}
// @__NO_SIDE_EFFECTS__
function ne(e, n) {
  var r;
  return (r = void 0 ) == null ? void 0 : r.get(n);
}
// @__NO_SIDE_EFFECTS__
function re$1(e) {
  var r, t;
  const n = typeof e;
  return n === "string" ? `"${e}"` : n === "number" || n === "bigint" || n === "boolean" ? `${e}` : n === "object" || n === "function" ? (e && ((t = (r = Object.getPrototypeOf(e)) == null ? void 0 : r.constructor) == null ? void 0 : t.name)) ?? "null" : n;
}
function f$2(e, n, r, t, s) {
  const u = s && "input" in s ? s.input : r.value, i = (s == null ? void 0 : s.expected) ?? e.expects ?? null, l = (s == null ? void 0 : s.received) ?? /* @__PURE__ */ re$1(u), o = {
    kind: e.kind,
    type: e.type,
    input: u,
    expected: i,
    received: l,
    message: `Invalid ${n}: ${i ? `Expected ${i} but r` : "R"}eceived ${l}`,
    requirement: e.requirement,
    path: s == null ? void 0 : s.path,
    issues: s == null ? void 0 : s.issues,
    lang: t.lang,
    abortEarly: t.abortEarly,
    abortPipeEarly: t.abortPipeEarly
  }, y = e.kind === "schema", p = (s == null ? void 0 : s.message) ?? e.message ?? /* @__PURE__ */ ne(e.reference, o.lang) ?? (y ? /* @__PURE__ */ ee$2(o.lang) : null) ?? t.message ?? /* @__PURE__ */ Z$2(o.lang);
  p && (o.message = typeof p == "function" ? (
    // @ts-expect-error
    p(o)
  ) : p), y && (r.typed = false), r.issues ? r.issues.push(o) : r.issues = [o];
}
// @__NO_SIDE_EFFECTS__
function h$2(e) {
  return {
    version: 1,
    vendor: "valibot",
    validate(n) {
      return e["~run"]({ value: n }, /* @__PURE__ */ N$1());
    }
  };
}
// @__NO_SIDE_EFFECTS__
function W$2(e, n) {
  return Object.hasOwn(e, n) && n !== "__proto__" && n !== "prototype" && n !== "constructor";
}
// @__NO_SIDE_EFFECTS__
function te$1(e, n) {
  const r = [...new Set(e)];
  return r.length > 1 ? `(${r.join(` ${n} `)})` : r[0] ?? "never";
}
var se = class extends Error {
  /**
   * Creates a Valibot error with useful information.
   *
   * @param issues The error issues.
   */
  constructor(e) {
    super(e[0].message), this.name = "ValiError", this.issues = e;
  }
};
// @__NO_SIDE_EFFECTS__
function L$1(e, n) {
  return {
    kind: "validation",
    type: "check",
    reference: L$1,
    async: false,
    expects: null,
    requirement: e,
    message: n,
    "~run"(r, t) {
      return r.typed && !this.requirement(r.value) && f$2(this, "input", r, t), r;
    }
  };
}
// @__NO_SIDE_EFFECTS__
function R$1(e) {
  return {
    kind: "validation",
    type: "integer",
    reference: R$1,
    async: false,
    expects: null,
    requirement: Number.isInteger,
    message: e,
    "~run"(n, r) {
      return n.typed && !this.requirement(n.value) && f$2(this, "integer", n, r), n;
    }
  };
}
// @__NO_SIDE_EFFECTS__
function d$1(e) {
  return {
    kind: "transformation",
    type: "transform",
    reference: d$1,
    async: false,
    operation: e,
    "~run"(n) {
      return n.value = this.operation(n.value), n;
    }
  };
}
// @__NO_SIDE_EFFECTS__
function U$1(e, n, r) {
  return typeof e.default == "function" ? (
    // @ts-expect-error
    e.default(n, r)
  ) : (
    // @ts-expect-error
    e.default
  );
}
// @__NO_SIDE_EFFECTS__
function ie$1(e, n) {
  return !e["~run"]({ value: n }, { abortEarly: true }).issues;
}
// @__NO_SIDE_EFFECTS__
function _(e) {
  return {
    kind: "schema",
    type: "boolean",
    reference: _,
    expects: "boolean",
    async: false,
    message: e,
    get "~standard"() {
      return /* @__PURE__ */ h$2(this);
    },
    "~run"(n, r) {
      return typeof n.value == "boolean" ? n.typed = true : f$2(this, "type", n, r), n;
    }
  };
}
// @__NO_SIDE_EFFECTS__
function z$2(e) {
  return {
    kind: "schema",
    type: "date",
    reference: z$2,
    expects: "Date",
    async: false,
    message: e,
    get "~standard"() {
      return /* @__PURE__ */ h$2(this);
    },
    "~run"(n, r) {
      return n.value instanceof Date ? isNaN(n.value) ? f$2(this, "type", n, r, {
        received: '"Invalid Date"'
      }) : n.typed = true : f$2(this, "type", n, r), n;
    }
  };
}
// @__NO_SIDE_EFFECTS__
function J$1(e, n) {
  return {
    kind: "schema",
    type: "instance",
    reference: J$1,
    expects: e.name,
    async: false,
    class: e,
    message: n,
    get "~standard"() {
      return /* @__PURE__ */ h$2(this);
    },
    "~run"(r, t) {
      return r.value instanceof this.class ? r.typed = true : f$2(this, "type", r, t), r;
    }
  };
}
// @__NO_SIDE_EFFECTS__
function A(e) {
  return {
    kind: "schema",
    type: "lazy",
    reference: A,
    expects: "unknown",
    async: false,
    getter: e,
    get "~standard"() {
      return /* @__PURE__ */ h$2(this);
    },
    "~run"(n, r) {
      return this.getter(n.value)["~run"](n, r);
    }
  };
}
// @__NO_SIDE_EFFECTS__
function k(e, n) {
  return {
    kind: "schema",
    type: "loose_object",
    reference: k,
    expects: "Object",
    async: false,
    entries: e,
    message: n,
    get "~standard"() {
      return /* @__PURE__ */ h$2(this);
    },
    "~run"(r, t) {
      var u;
      const s = r.value;
      if (s && typeof s == "object") {
        r.typed = true, r.value = {};
        for (const i in this.entries) {
          const l = this.entries[i];
          if (i in s || (l.type === "exact_optional" || l.type === "optional" || l.type === "nullish") && // @ts-expect-error
          l.default !== void 0) {
            const o = i in s ? (
              // @ts-expect-error
              s[i]
            ) : /* @__PURE__ */ U$1(l), y = l["~run"]({ value: o }, t);
            if (y.issues) {
              const p = {
                type: "object",
                origin: "value",
                input: s,
                key: i,
                value: o
              };
              for (const m of y.issues)
                m.path ? m.path.unshift(p) : m.path = [p], (u = r.issues) == null || u.push(m);
              if (r.issues || (r.issues = y.issues), t.abortEarly) {
                r.typed = false;
                break;
              }
            }
            y.typed || (r.typed = false), r.value[i] = y.value;
          } else if (l.type !== "exact_optional" && l.type !== "optional" && l.type !== "nullish" && (f$2(this, "key", r, t, {
            input: void 0,
            expected: `"${i}"`,
            path: [
              {
                type: "object",
                origin: "key",
                input: s,
                key: i,
                // @ts-expect-error
                value: s[i]
              }
            ]
          }), t.abortEarly))
            break;
        }
        if (!r.issues || !t.abortEarly)
          for (const i in s)
            /* @__PURE__ */ W$2(s, i) && !(i in this.entries) && (r.value[i] = s[i]);
      } else
        f$2(this, "type", r, t);
      return r;
    }
  };
}
// @__NO_SIDE_EFFECTS__
function E$1(e) {
  return {
    kind: "schema",
    type: "number",
    reference: E$1,
    expects: "number",
    async: false,
    message: e,
    get "~standard"() {
      return /* @__PURE__ */ h$2(this);
    },
    "~run"(n, r) {
      return typeof n.value == "number" && !isNaN(n.value) ? n.typed = true : f$2(this, "type", n, r), n;
    }
  };
}
// @__NO_SIDE_EFFECTS__
function c$3(e, n) {
  return {
    kind: "schema",
    type: "optional",
    reference: c$3,
    expects: `(${e.expects} | undefined)`,
    async: false,
    wrapped: e,
    default: n,
    get "~standard"() {
      return /* @__PURE__ */ h$2(this);
    },
    "~run"(r, t) {
      return r.value === void 0 && (this.default !== void 0 && (r.value = /* @__PURE__ */ U$1(this, r, t)), r.value === void 0) ? (r.typed = true, r) : this.wrapped["~run"](r, t);
    }
  };
}
// @__NO_SIDE_EFFECTS__
function V$2(e, n, r) {
  return {
    kind: "schema",
    type: "record",
    reference: V$2,
    expects: "Object",
    async: false,
    key: e,
    value: n,
    message: r,
    get "~standard"() {
      return /* @__PURE__ */ h$2(this);
    },
    "~run"(t, s) {
      var i, l;
      const u = t.value;
      if (u && typeof u == "object") {
        t.typed = true, t.value = {};
        for (const o in u)
          if (/* @__PURE__ */ W$2(u, o)) {
            const y = u[o], p = this.key["~run"]({ value: o }, s);
            if (p.issues) {
              const S = {
                type: "object",
                origin: "key",
                input: u,
                key: o,
                value: y
              };
              for (const g of p.issues)
                g.path = [S], (i = t.issues) == null || i.push(g);
              if (t.issues || (t.issues = p.issues), s.abortEarly) {
                t.typed = false;
                break;
              }
            }
            const m = this.value["~run"](
              { value: y },
              s
            );
            if (m.issues) {
              const S = {
                type: "object",
                origin: "value",
                input: u,
                key: o,
                value: y
              };
              for (const g of m.issues)
                g.path ? g.path.unshift(S) : g.path = [S], (l = t.issues) == null || l.push(g);
              if (t.issues || (t.issues = m.issues), s.abortEarly) {
                t.typed = false;
                break;
              }
            }
            (!p.typed || !m.typed) && (t.typed = false), p.typed && (t.value[p.value] = m.value);
          }
      } else
        f$2(this, "type", t, s);
      return t;
    }
  };
}
// @__NO_SIDE_EFFECTS__
function a$1(e) {
  return {
    kind: "schema",
    type: "string",
    reference: a$1,
    expects: "string",
    async: false,
    message: e,
    get "~standard"() {
      return /* @__PURE__ */ h$2(this);
    },
    "~run"(n, r) {
      return typeof n.value == "string" ? n.typed = true : f$2(this, "type", n, r), n;
    }
  };
}
// @__NO_SIDE_EFFECTS__
function O$1(e) {
  let n;
  if (e)
    for (const r of e)
      n ? n.push(...r.issues) : n = r.issues;
  return n;
}
// @__NO_SIDE_EFFECTS__
function $$1(e, n) {
  return {
    kind: "schema",
    type: "union",
    reference: $$1,
    expects: /* @__PURE__ */ te$1(
      e.map((r) => r.expects),
      "|"
    ),
    async: false,
    options: e,
    message: n,
    get "~standard"() {
      return /* @__PURE__ */ h$2(this);
    },
    "~run"(r, t) {
      let s, u, i;
      for (const l of this.options) {
        const o = l["~run"]({ value: r.value }, t);
        if (o.typed)
          if (o.issues)
            u ? u.push(o) : u = [o];
          else {
            s = o;
            break;
          }
        else
          i ? i.push(o) : i = [o];
      }
      if (s)
        return s;
      if (u) {
        if (u.length === 1)
          return u[0];
        f$2(this, "type", r, t, {
          issues: /* @__PURE__ */ O$1(u)
        }), r.typed = true;
      } else {
        if ((i == null ? void 0 : i.length) === 1)
          return i[0];
        f$2(this, "type", r, t, {
          issues: /* @__PURE__ */ O$1(i)
        });
      }
      return r;
    }
  };
}
// @__NO_SIDE_EFFECTS__
function q() {
  return {
    kind: "schema",
    type: "unknown",
    reference: q,
    expects: "unknown",
    async: false,
    get "~standard"() {
      return /* @__PURE__ */ h$2(this);
    },
    "~run"(e) {
      return e.typed = true, e;
    }
  };
}
function B$1(e, n, r) {
  const t = e["~run"]({ value: n }, /* @__PURE__ */ N$1(r));
  if (t.issues)
    throw new se(t.issues);
  return t.value;
}
// @__NO_SIDE_EFFECTS__
function v$1(...e) {
  return {
    ...e[0],
    pipe: e,
    get "~standard"() {
      return /* @__PURE__ */ h$2(this);
    },
    "~run"(n, r) {
      for (const t of e)
        if (t.kind !== "metadata") {
          if (n.issues && (t.kind === "schema" || t.kind === "transformation")) {
            n.typed = false;
            break;
          }
          (!n.issues || !r.abortEarly && !r.abortPipeEarly) && (n = t["~run"](n, r));
        }
      return n;
    }
  };
}
function ue$1(e) {
  return e.replace(/_[a-z]/g, (n) => n[1].toUpperCase());
}
function ae$1(e) {
  return Object.entries(e).reduce((n, [r, t]) => (n[ue$1(r)] = t, n), {});
}
function w$1(e) {
  const n = ae$1(e);
  for (const r in n) {
    const t = n[r];
    t && typeof t == "object" && !(t instanceof Date) && (n[r] = Array.isArray(t) ? t.map(w$1) : w$1(t));
  }
  return n;
}
function I$2(e) {
  return /* @__PURE__ */ d$1((n) => e ? w$1(n) : n);
}
function M(e) {
  return (n) => /* @__PURE__ */ v$1(
    e,
    I$2(n)
  );
}
function T(e) {
  return (n, r) => B$1(
    /* @__PURE__ */ v$1(e, I$2(r)),
    n
  );
}
function oe() {
  return /* @__PURE__ */ d$1(JSON.parse);
}
function C(e) {
  const n = M(e);
  return (r) => /* @__PURE__ */ v$1(
    /* @__PURE__ */ a$1(),
    oe(),
    n(r)
  );
}
function ce$1(e) {
  return /* @__PURE__ */ d$1((n) => {
    const r = {};
    return new URLSearchParams(n).forEach((t, s) => {
      const u = r[s];
      Array.isArray(u) ? u.push(t) : u === void 0 ? r[s] = t : r[s] = [u, t];
    }), B$1(e, r);
  });
}
function K$2(e) {
  return (n) => /* @__PURE__ */ v$1(
    /* @__PURE__ */ $$1([/* @__PURE__ */ a$1(), /* @__PURE__ */ J$1(URLSearchParams)]),
    ce$1(e),
    I$2(n)
  );
}
const Q$1 = /* @__PURE__ */ c$3(/* @__PURE__ */ A(() => he$1())), le$2 = /* @__PURE__ */ k({
  id: /* @__PURE__ */ E$1(),
  photo_url: /* @__PURE__ */ c$3(/* @__PURE__ */ a$1()),
  type: /* @__PURE__ */ a$1(),
  title: /* @__PURE__ */ a$1(),
  username: /* @__PURE__ */ c$3(/* @__PURE__ */ a$1())
}), pe$2 = /* @__PURE__ */ k({
  added_to_attachment_menu: /* @__PURE__ */ c$3(/* @__PURE__ */ _()),
  allows_write_to_pm: /* @__PURE__ */ c$3(/* @__PURE__ */ _()),
  first_name: /* @__PURE__ */ a$1(),
  id: /* @__PURE__ */ E$1(),
  is_bot: /* @__PURE__ */ c$3(/* @__PURE__ */ _()),
  is_premium: /* @__PURE__ */ c$3(/* @__PURE__ */ _()),
  last_name: /* @__PURE__ */ c$3(/* @__PURE__ */ a$1()),
  language_code: /* @__PURE__ */ c$3(/* @__PURE__ */ a$1()),
  photo_url: /* @__PURE__ */ c$3(/* @__PURE__ */ a$1()),
  username: /* @__PURE__ */ c$3(/* @__PURE__ */ a$1())
}), fe = /* @__PURE__ */ k({
  auth_date: /* @__PURE__ */ v$1(
    /* @__PURE__ */ a$1(),
    /* @__PURE__ */ d$1((e) => new Date(Number(e) * 1e3)),
    /* @__PURE__ */ z$2()
  ),
  can_send_after: /* @__PURE__ */ c$3(/* @__PURE__ */ v$1(/* @__PURE__ */ a$1(), /* @__PURE__ */ d$1(Number), /* @__PURE__ */ R$1())),
  chat: /* @__PURE__ */ c$3(/* @__PURE__ */ A(() => ye$2())),
  chat_type: /* @__PURE__ */ c$3(/* @__PURE__ */ a$1()),
  chat_instance: /* @__PURE__ */ c$3(/* @__PURE__ */ a$1()),
  hash: /* @__PURE__ */ a$1(),
  query_id: /* @__PURE__ */ c$3(/* @__PURE__ */ a$1()),
  receiver: Q$1,
  start_param: /* @__PURE__ */ c$3(/* @__PURE__ */ a$1()),
  signature: /* @__PURE__ */ a$1(),
  user: Q$1
}), ye$2 = C(le$2), he$1 = C(pe$2), F$1 = K$2(fe);
function H$2(e) {
  return /^#[\da-f]{6}$/i.test(e);
}
const be$1 = M(
  /* @__PURE__ */ V$2(
    /* @__PURE__ */ a$1(),
    /* @__PURE__ */ v$1(
      /* @__PURE__ */ $$1([/* @__PURE__ */ a$1(), /* @__PURE__ */ E$1()]),
      /* @__PURE__ */ d$1((e) => typeof e == "number" ? `#${(e & 16777215).toString(16).padStart(6, "0")}` : e),
      /* @__PURE__ */ L$1(H$2)
    )
  )
), x$2 = /* @__PURE__ */ c$3(
  /* @__PURE__ */ v$1(/* @__PURE__ */ a$1(), /* @__PURE__ */ d$1((e) => e === "1"))
), G$1 = C(be$1()), de$1 = /* @__PURE__ */ k({
  tgWebAppBotInline: x$2,
  tgWebAppData: /* @__PURE__ */ c$3(F$1()),
  tgWebAppDefaultColors: /* @__PURE__ */ c$3(G$1()),
  tgWebAppFullscreen: x$2,
  tgWebAppPlatform: /* @__PURE__ */ a$1(),
  tgWebAppShowSettings: x$2,
  tgWebAppStartParam: /* @__PURE__ */ c$3(/* @__PURE__ */ a$1()),
  tgWebAppThemeParams: G$1(),
  tgWebAppVersion: /* @__PURE__ */ a$1()
}), X$1 = K$2(de$1), _e = T(X$1()), Se$2 = /* @__PURE__ */ k({
  eventType: /* @__PURE__ */ a$1(),
  eventData: /* @__PURE__ */ c$3(/* @__PURE__ */ q())
});
function De$2(e) {
  try {
    return /* @__PURE__ */ ie$1(X$1(), e);
  } catch {
    return false;
  }
}

function pe$1(n){return {all:n=n||new Map,on:function(t,e){var i=n.get(t);i?i.push(e):n.set(t,[e]);},off:function(t,e){var i=n.get(t);i&&(e?i.splice(i.indexOf(e)>>>0,1):n.set(t,[]));},emit:function(t,e){var i=n.get(t);i&&i.slice().map(function(n){n(e);}),(i=n.get("*"))&&i.slice().map(function(n){n(t,e);});}}}

let r;
function y$1(e, c) {
  r && r.set(e, c) || c();
}
function m(e) {
  if (r)
    return e();
  r = /* @__PURE__ */ new Map();
  try {
    e();
  } finally {
    r.forEach((c) => c()), r = void 0;
  }
}
// @__NO_SIDE_EFFECTS__
function S(e, c) {
  c || (c = {});
  const g = c.equals || Object.is;
  let u = [], s = e;
  const i = (t) => {
    if (!g(s, t)) {
      const l = s;
      s = t, y$1(o, () => {
        [...u].forEach(([f, d]) => {
          f(t, l), d && n(f, true);
        });
      });
    }
  };
  function a(t) {
    const l = typeof t != "object" ? { once: t } : t;
    return {
      once: l.once || false,
      signal: l.signal || false
    };
  }
  const n = (t, l) => {
    const f = a(l), d = u.findIndex(([h, p]) => h === t && p.once === f.once && p.signal === f.signal);
    d >= 0 && u.splice(d, 1);
  }, o = Object.assign(
    function() {
      return j$2(o), s;
    },
    {
      destroy() {
        u = [];
      },
      set: i,
      reset() {
        i(e);
      },
      sub(t, l) {
        return u.push([t, a(l)]), () => n(t, l);
      },
      unsub: n,
      unsubAll() {
        u = u.filter((t) => t[1].signal);
      }
    }
  );
  return o;
}
const b$1 = [];
function j$2(e) {
  b$1.length && b$1[b$1.length - 1].add(e);
}
// @__NO_SIDE_EFFECTS__
function x$1(e, c) {
  let g = /* @__PURE__ */ new Set(), u;
  function s() {
    return u || (u = /* @__PURE__ */ S(a(), c));
  }
  function i() {
    s().set(a());
  }
  function a() {
    g.forEach((t) => {
      t.unsub(i, { signal: true });
    });
    const n = /* @__PURE__ */ new Set();
    let o;
    b$1.push(n);
    try {
      o = e();
    } finally {
      b$1.pop();
    }
    return n.forEach((t) => {
      t.sub(i, { signal: true });
    }), g = n, o;
  }
  return Object.assign(function() {
    return s()();
  }, {
    destroy() {
      s().destroy();
    },
    sub(...n) {
      return s().sub(...n);
    },
    unsub(...n) {
      s().unsub(...n);
    },
    unsubAll(...n) {
      s().unsubAll(...n);
    }
  });
}

var f$1 = Object.defineProperty;
var u$1 = (r, t, e) => t in r ? f$1(r, t, { enumerable: true, configurable: true, writable: true, value: e }) : r[t] = e;
var c$2 = (r, t, e) => u$1(r, typeof t != "symbol" ? t + "" : t, e);
function a(r, t) {
  return (e) => e instanceof r && e.type === t;
}
function p$2(r, t) {
  t || (t = []);
  const e = Symbol(r);
  class n extends Error {
    constructor(...i) {
      const o = typeof t == "function" ? t(...i) : typeof t == "string" ? [t] : t || [];
      super(...o);
      c$2(this, "type", e);
      this.name = r;
    }
  }
  return Object.defineProperty(n, "name", { value: r }), [n, a(n, e)];
}
function l(r, t, e) {
  const n = Symbol(r);
  class s extends p$2(r, e)[0] {
    constructor(...o) {
      super(...o);
      c$2(this, "data");
      c$2(this, "type", n);
      this.data = t(...o);
    }
  }
  return Object.defineProperty(s, "name", { value: r }), [s, a(s, n)];
}

function H$1(e) {
  return is$1(
    looseObject({ TelegramWebviewProxy: looseObject({ postEvent: function_() }) }),
    e
  );
}
function K$1() {
  try {
    return window.self !== window.top;
  } catch {
    return true;
  }
}
function le$1(e, t) {
  const r = /* @__PURE__ */ new Map(), n = pe$1(), a = (o, s, c) => {
    c || (c = false);
    const i = r.get(o) || /* @__PURE__ */ new Map();
    r.set(o, i);
    const _ = i.get(s) || [];
    i.set(s, _);
    const l = _.findIndex((w) => w[1] === c);
    if (l >= 0 && (n.off(o, _[l][0]), _.splice(l, 1), !_.length && (i.delete(s), !i.size))) {
      const w = r.size;
      r.delete(o), w && !r.size && t();
    }
  };
  return [
    function(s, c, i) {
      !r.size && e();
      const _ = () => {
        a(s, c, i);
      }, l = (...M) => {
        i && _(), s === "*" ? c(M) : c(...M);
      };
      n.on(s, l);
      const w = r.get(s) || /* @__PURE__ */ new Map();
      r.set(s, w);
      const T = w.get(c) || [];
      return w.set(c, T), T.push([l, i || false]), _;
    },
    a,
    // eslint-disable-next-line @typescript-eslint/unbound-method
    n.emit,
    function() {
      const s = r.size;
      n.all.clear(), r.clear(), s && t();
    }
  ];
}
function v(e, t) {
  window.dispatchEvent(new MessageEvent("message", {
    data: JSON.stringify({ eventType: e, eventData: t }),
    // We specify window.parent to imitate the case, the parent iframe sent us this event.
    source: window.parent
  }));
}
let h$1 = false;
const f = S(O$2("Bridge", {
  bgColor: "#9147ff",
  textColor: "white",
  shouldLog() {
    return h$1;
  }
}));
function Y$1(e, t, r, n) {
  Object.defineProperty(e, t, {
    enumerable: true,
    configurable: true,
    get: r,
    set: n
  });
}
function W$1(e, t) {
  const r = e[t];
  Y$1(e, t, () => r, (n) => {
    Object.entries(n).forEach(([a, o]) => {
      r[a] = o;
    });
  });
}
function U(e, t, r) {
  Object.defineProperty(e, t, {
    enumerable: true,
    configurable: true,
    writable: true,
    value: r
  });
}
function E(e, t, r) {
  const n = e[t], a = [r];
  typeof n == "function" && a.push(n);
  const o = (...c) => {
    a.forEach((i) => {
      i(...c);
    });
  }, s = Object.assign((...c) => {
    o(...c);
  }, {
    // Unwraps the composer.
    unwrap() {
      const { length: c } = a;
      if (c === 1) {
        delete e[t];
        return;
      }
      if (c === 2) {
        U(e, t, a[1]);
        return;
      }
      a.unshift(1), U(e, t, o);
    }
  });
  Y$1(
    e,
    t,
    () => s,
    (c) => {
      a.push(c);
    }
  );
}
const we$1 = {
  clipboard_text_received: looseObject({
    req_id: string(),
    data: nullish(string())
  }),
  custom_method_invoked: looseObject({
    req_id: string(),
    result: optional(unknown()),
    error: optional(string())
  }),
  popup_closed: nullish(
    looseObject({ button_id: nullish(string(), () => {
    }) }),
    {}
  ),
  viewport_changed: looseObject({
    height: number(),
    width: nullish(number(), () => window.innerWidth),
    is_state_stable: boolean(),
    is_expanded: boolean()
  }),
  theme_changed: looseObject({
    theme_params: be$1()
  })
};
function I$1(e) {
  if (e.source !== window.parent)
    return;
  let t;
  try {
    t = parse(pipe(string(), oe(), Se$2), e.data);
  } catch {
    return;
  }
  const { eventType: r, eventData: n } = t, a = we$1[r];
  let o;
  try {
    o = a ? parse(a, n) : n;
  } catch (s) {
    return f().forceError(
      [
        `An error occurred processing the "${r}" event from the Telegram application.`,
        "Please, file an issue here:",
        "https://github.com/Telegram-Mini-Apps/telegram-apps/issues/new/choose"
      ].join(`
`),
      t,
      s
    );
  }
  ge$1(r, o);
}
const [
  X,
  me$1,
  ge$1] = le$1(
  () => {
    const e = window;
    !e.TelegramGameProxy && (e.TelegramGameProxy = {}), E(e.TelegramGameProxy, "receiveEvent", v), W$1(e, "TelegramGameProxy"), !e.Telegram && (e.Telegram = {}), !e.Telegram.WebView && (e.Telegram.WebView = {}), E(e.Telegram.WebView, "receiveEvent", v), W$1(e.Telegram, "WebView"), E(e, "TelegramGameProxy_receiveEvent", v), window.addEventListener("message", I$1);
  },
  () => {
    [
      ["TelegramGameProxy_receiveEvent"],
      ["TelegramGameProxy", "receiveEvent"],
      ["Telegram", "WebView", "receiveEvent"]
    ].forEach((e) => {
      const t = window;
      let r = [void 0, t];
      for (const o of e)
        if (r = [r[1], r[1][o]], !r[1])
          return;
      const [n, a] = r;
      "unwrap" in a && (a.unwrap(), n && n !== t && !Object.keys(n).length && delete t[e[0]]);
    }), window.removeEventListener("message", I$1);
  }
); p$2(
  "MethodUnsupportedError",
  (e, t) => [
    `Method "${e}" is unsupported in Mini Apps version ${t}`
  ]
); p$2(
  "MethodParameterUnsupportedError",
  (e, t, r) => [
    `Parameter "${t}" of "${e}" method is unsupported in Mini Apps version ${r}`
  ]
); const [
  ye$1] = l(
  "LaunchParamsRetrieveError",
  (e) => ({ errors: e }),
  (e) => [
    [
      "Unable to retrieve launch parameters from any known source. Perhaps, you have opened your app outside Telegram?",
      "📖 Refer to docs for more information:",
      "https://docs.telegram-mini-apps.com/packages/telegram-apps-bridge/environment",
      "",
      "Collected errors:",
      ...e.map(([t, r]) => `Source: ${t} / ${r instanceof Error ? r.message : String(r)}`)
    ].join(`
`)
  ]
); p$2(
  "InvalidLaunchParamsError",
  (e, t) => [
    `Invalid value for launch params: ${e}`,
    { cause: t }
  ]
); const [Ee$1] = p$2("UnknownEnvError"), [
  Pe$1] = p$2(
  "InvokeCustomMethodError",
  (e) => [`Server returned error: ${e}`]
), g = S((...e) => {
  try {
    window.parent.postMessage(...e);
  } catch (t) {
    t instanceof SyntaxError ? f().forceError(
      "Unable to call window.parent.postMessage due to incorrectly configured target origin. Use the setTargetOrigin method to allow this origin to receive events",
      t
    ) : f().forceError(t);
  }
}), ke$1 = (...e) => g()(...e), x = S("https://web.telegram.org");
function Z$1(e, t) {
  f().log("Posting event:", t ? { eventType: e, eventData: t } : { eventType: e });
  const r = window, n = JSON.stringify({ eventType: e, eventData: t });
  if (K$1())
    return ke$1(n, x());
  if (H$1(r)) {
    r.TelegramWebviewProxy.postEvent(e, JSON.stringify(t));
    return;
  }
  if (is$1(looseObject({ external: looseObject({ notify: function_() }) }), r)) {
    r.external.notify(n);
    return;
  }
  throw new Ee$1();
}
function V$1(e, t, r) {
  r || (r = {});
  const { capture: n } = r, [a, o] = L$2();
  return new m$1((s) => {
    (Array.isArray(t) ? t : [t]).forEach((c) => {
      a(
        X(c, (i) => {
          (!n || (Array.isArray(t) ? n({
            event: c,
            payload: i
          }) : n(i))) && s(i);
        })
      );
    }), (r.postEvent || Z$1)(e, r.params);
  }, r).finally(o);
}
const R = "launchParams";
function j$1(e) {
  return e.replace(/^[^?#]*[?#]/, "").replace(/[?#]/g, "&");
}
function ee$1() {
  const e = [];
  for (const [t, r] of [
    // Try to retrieve launch parameters from the current location. This method can return
    // nothing in case, location was changed, and then the page was reloaded.
    [() => j$1(window.location.href), "window.location.href"],
    // Then, try using the lower level API - window.performance.
    [() => {
      const n = performance.getEntriesByType("navigation")[0];
      return n && j$1(n.name);
    }, "performance navigation entries"],
    [() => T$1(R), "local storage"]
  ]) {
    const n = t();
    if (!n) {
      e.push([r, new Error("Source is empty")]);
      continue;
    }
    if (De$2(n))
      return w$2(R, n), n;
    try {
      _e(n);
    } catch (a) {
      e.push([r, a]);
    }
  }
  throw new ye$1(e);
}
function Se$1(e) {
  const t = _e(ee$1());
  return t;
}
function De$1(e, t) {
  try {
      return Se$1(), !0;
    } catch {
      return false;
    }
  return m$1.fn(async (r) => {
    if (H$1(window))
      return true;
    try {
      return await V$1("web_app_request_theme", "theme_changed", r), !0;
    } catch {
      return false;
    }
  }, { timeout: 100 });
}
function Be$1() {
  return new URLSearchParams(ee$1()).get("tgWebAppData") || void 0;
}
function xe$1(e) {
  return ({ req_id: t }) => t === e;
}
function $(e) {
  return e.split(".").map(Number);
}
function Te$1(e, t) {
  const r = $(e), n = $(t), a = Math.max(r.length, n.length);
  for (let o = 0; o < a; o += 1) {
    const s = r[o] || 0, c = n[o] || 0;
    if (s !== c)
      return s > c ? 1 : -1;
  }
  return 0;
}
function p$1(e, t) {
  return Te$1(e, t) <= 0;
}
function z$1(e, t, r) {
  if (typeof r == "string") {
    if (e === "web_app_open_link") {
      if (t === "try_instant_view")
        return p$1("6.4", r);
      if (t === "try_browser")
        return p$1("7.6", r);
    }
    if (e === "web_app_set_header_color" && t === "color")
      return p$1("6.9", r);
    if (e === "web_app_close" && t === "return_back")
      return p$1("7.6", r);
    if (e === "web_app_setup_main_button" && t === "has_shine_effect")
      return p$1("7.10", r);
  }
  switch (e) {
    case "web_app_open_tg_link":
    case "web_app_open_invoice":
    case "web_app_setup_back_button":
    case "web_app_set_background_color":
    case "web_app_set_header_color":
    case "web_app_trigger_haptic_feedback":
      return p$1("6.1", t);
    case "web_app_open_popup":
      return p$1("6.2", t);
    case "web_app_close_scan_qr_popup":
    case "web_app_open_scan_qr_popup":
    case "web_app_read_text_from_clipboard":
      return p$1("6.4", t);
    case "web_app_switch_inline_query":
      return p$1("6.7", t);
    case "web_app_invoke_custom_method":
    case "web_app_request_write_access":
    case "web_app_request_phone":
      return p$1("6.9", t);
    case "web_app_setup_settings_button":
      return p$1("6.10", t);
    case "web_app_biometry_get_info":
    case "web_app_biometry_open_settings":
    case "web_app_biometry_request_access":
    case "web_app_biometry_request_auth":
    case "web_app_biometry_update_token":
      return p$1("7.2", t);
    case "web_app_setup_swipe_behavior":
      return p$1("7.7", t);
    case "web_app_share_to_story":
      return p$1("7.8", t);
    case "web_app_setup_secondary_button":
    case "web_app_set_bottom_bar_color":
      return p$1("7.10", t);
    case "web_app_request_safe_area":
    case "web_app_request_content_safe_area":
    case "web_app_request_fullscreen":
    case "web_app_exit_fullscreen":
    case "web_app_set_emoji_status":
    case "web_app_add_to_home_screen":
    case "web_app_check_home_screen":
    case "web_app_request_emoji_status_access":
    case "web_app_check_location":
    case "web_app_open_location_settings":
    case "web_app_request_file_download":
    case "web_app_request_location":
    case "web_app_send_prepared_message":
    case "web_app_start_accelerometer":
    case "web_app_start_device_orientation":
    case "web_app_start_gyroscope":
    case "web_app_stop_accelerometer":
    case "web_app_stop_device_orientation":
    case "web_app_stop_gyroscope":
    case "web_app_toggle_orientation_lock":
      return p$1("8.0", t);
    case "web_app_device_storage_clear":
    case "web_app_device_storage_get_key":
    case "web_app_device_storage_save_key":
    case "web_app_secure_storage_clear":
    case "web_app_secure_storage_get_key":
    case "web_app_secure_storage_restore_key":
    case "web_app_secure_storage_save_key":
      return p$1("9.0", t);
    case "web_app_hide_keyboard":
      return p$1("9.1", t);
    default:
      return [
        "iframe_ready",
        "iframe_will_reload",
        "web_app_close",
        "web_app_data_send",
        "web_app_expand",
        "web_app_open_link",
        "web_app_ready",
        "web_app_request_theme",
        "web_app_request_viewport",
        "web_app_setup_main_button",
        "web_app_setup_closing_behavior"
      ].includes(e);
  }
}
function Ke$1(e, t, r, n) {
  return V$1("web_app_invoke_custom_method", "custom_method_invoked", {
    ...n || {},
    params: { method: e, params: t, req_id: r },
    capture: xe$1(r)
  }).then(({ result: a, error: o }) => {
    if (o)
      throw new Pe$1(o);
    return a;
  });
}

function i$1() {
  return performance.getEntriesByType("navigation")[0];
}
function c$1() {
  const t = i$1();
  return !!t && t.type === "reload";
}

// @__NO_SIDE_EFFECTS__
function z(e, t) {
  return S(e, t);
}
// @__NO_SIDE_EFFECTS__
function c(e, t) {
  return x$1(e, t);
}
// @__NO_SIDE_EFFECTS__
function u(e, t) {
  const o = /* @__PURE__ */ z(e, t);
  return [o, /* @__PURE__ */ c(o)];
}
const je = /* @__PURE__ */ z(0), Po = /* @__PURE__ */ z(Z$1), [oo, le] = /* @__PURE__ */ u({
  tgWebAppPlatform: "unknown",
  tgWebAppVersion: "0.0"
}), O = /* @__PURE__ */ c(() => le().tgWebAppVersion);
function To() {
  return je.set(je() + 1), je().toString();
}
function W(e, t, o) {
  return Ke$1(e, t, To(), {
    ...o || {},
    postEvent: i
  });
}
const d = (e, t, o) => (o || (o = {}), o.postEvent || (o.postEvent = i), V$1(e, t, o)), i = (e, t) => Po()(e, t);
function L(e) {
  return [e];
}
const [
  ot] = p$2("CSSVarsBoundError", "CSS variables are already bound"), [
  ko] = p$2("NotAvailableError", L); p$2("InvalidEnvError", L); const [
  Z] = p$2("FunctionNotAvailableError", L), [
  y] = p$2(
  "InvalidArgumentsError",
  (e, t) => [e, { cause: t }]
), [
  On] = p$2("ConcurrentCallError", L), [
  In] = p$2(
  "SetEmojiStatusError",
  (e) => [`Failed to set emoji status: ${e}`]
), [
  Oo] = p$2("AccessDeniedError", L), [
  Vn] = p$2("FullscreenFailedError", L); p$2("ShareMessageError", L); const [
  st] = p$2("UnknownThemeParamsKeyError", (e) => [`Unknown theme params key passed: ${e}`]);
function so() {
  return typeof window > "u";
}
// @__NO_SIDE_EFFECTS__
function p(e, t, o) {
  o || (o = {});
  const {
    isSupported: s,
    isMounted: n,
    isMounting: r,
    component: a,
    supports: l
  } = o || {}, P = `${a ? `${a}.` : ""}${e}()`, T = s ? Array.isArray(s) || typeof s == "object" && "any" in s ? s : [s] : void 0;
  function X(g) {
    if (l) {
      const _ = l[g];
      return z$1(_[0], _[1], O());
    }
    return true;
  }
  function k() {
    if (!T)
      return;
    function g(U) {
      return typeof U == "function" ? U() : z$1(U, O()) ? void 0 : `it is unsupported in Mini Apps version ${O()}`;
    }
    const _ = Array.isArray(T) ? T : T.any, x = _.map(g).filter(Boolean);
    return Array.isArray(T) ? x[0] : x.length === _.length ? x[x.length - 1] : void 0;
  }
  function cn(...g) {
    for (const _ in l)
      if (l[_][2](...g) && !X(_))
        return `option ${_} is not supported in Mini Apps version ${O()}`;
  }
  let _e;
  if (l) {
    _e = {};
    for (const g in l)
      _e[g] = /* @__PURE__ */ c(() => X(g));
  }
  const Kt = /* @__PURE__ */ c(() => !k()), Yt = /* @__PURE__ */ c(() => O() !== "0.0"), Xt = /* @__PURE__ */ c(() => !n || n()), Zt = /* @__PURE__ */ c(
    () => De$1() && !so() && Yt() && Kt() && Xt()
  );
  return Object.assign(
    (...g) => {
      const _ = `Unable to call the ${P} ${a ? "method" : "function"}:`;
      if (so() || !De$1())
        throw new Z(`${_} it can't be called outside Mini Apps`);
      if (!Yt())
        throw new Z(`${_} the SDK was not initialized. Use the SDK init() function`);
      const x = k();
      if (x)
        throw new Z(`${_} ${x}`);
      const U = cn(...g);
      if (U)
        throw new Z(`${_} ${U}`);
      if (!Xt()) {
        const un = r && r() ? "mounting. Wait for the mount completion" : `unmounted. Use the ${a}.mount() method`;
        throw new Z(`${_} the component is ${un}`);
      }
      return t(...g);
    },
    t,
    {
      isAvailable: Zt,
      ifAvailable(...g) {
        return Zt() ? [true, t(...g)] : [false];
      }
    },
    T ? { isSupported: Kt } : {},
    _e ? { supports: _e } : {}
  );
}
function we(e, t) {
  return t || (t = {}), (o, s, n, r) => /* @__PURE__ */ p(o, s, {
    ...t,
    isSupported: n || t.isSupported,
    supports: r,
    component: e
  });
}
function I(e, t, o) {
  return we(e, { isSupported: o, isMounted: t });
}
function w(e, t) {
  return we(e, { isSupported: t });
}
const $e = "web_app_setup_back_button", Io = "back_button_pressed", Me = "backButton", [no, xn] = /* @__PURE__ */ u(false), [he] = /* @__PURE__ */ u(false), Vo = I(Me, he, $e), nt = w(Me, $e), Hn = Vo("hide", () => {
  rt(false);
}); nt("mount", () => {
  he() || (rt(c$1() && T$1(Me) || false), he.set(true));
});
function rt(e) {
  e !== no() && (i($e, { is_visible: e }), w$2(Me, e), no.set(e));
}
const Rn = nt(
  "onClick",
  (e) => X(Io, e)
), jn = nt(
  "offClick",
  (e) => {
    me$1(Io, e);
  }
), Fn = Vo("show", () => {
  rt(true);
});
function b(e, t, o) {
  o || (o = {});
  const {
    promise: s,
    error: n
  } = o, [r, a] = s ? [s, /* @__PURE__ */ c(s)] : /* @__PURE__ */ u(), [l, P] = n ? [n, /* @__PURE__ */ c(n)] : /* @__PURE__ */ u();
  return [
    Object.assign((...T) => {
      if (r()) {
        const k = new On(t);
        return l.set(k), m$1.reject(k);
      }
      m(() => {
        r.set(e(...T)), l.set(void 0);
      });
      let X;
      return r().catch((k) => {
        throw X = k, k;
      }).finally(() => {
        m(() => {
          r.set(void 0), l.set(X);
        });
      });
    }, e),
    [r, a, /* @__PURE__ */ c(() => !!r())],
    [l, P]
  ];
}
// @__NO_SIDE_EFFECTS__
function pe(e, t, o) {
  const [s, ...n] = b(t, `The ${e} component is already mounting`), [r, a] = /* @__PURE__ */ u(false);
  return [
    (...l) => r() ? m$1.resolve() : s(...l).then((P) => {
      m(() => {
        r.set(!0), o(P);
      });
    }),
    ...n,
    [r, a]
  ];
}
const [at] = /* @__PURE__ */ u({
  available: false,
  type: "",
  accessGranted: false,
  accessRequested: false,
  deviceId: "",
  tokenSaved: false
}), ro = "web_app_biometry_get_info", Wn = /* @__PURE__ */ p(
  "requestBiometry",
  (e) => d(ro, "biometry_info_received", e),
  { isSupported: ro }
);
function qo(e) {
  if (!M$1(e))
    throw e;
}
function Q(e) {
  const t = e();
  t && t.catch(qo).cancel();
}
const re = "biometry", Ae = "web_app_biometry_request_auth", it = "biometry_info_received", xo = (e) => {
  ve(ct(e));
};
function Do() {
  throw new ko("Biometry is not available");
}
function ct(e) {
  let t = false, o = false, s = "", n = false, r = "", a = false;
  return e.available && (t = true, o = e.token_saved, s = e.device_id, n = e.access_requested, r = e.type, a = e.access_granted), { available: t, tokenSaved: o, deviceId: s, type: r, accessGranted: a, accessRequested: n };
}
const [
  Kn,
  Yn,
  Xn,
  No
] = /* @__PURE__ */ pe(
  re,
  (e) => {
    const t = c$1() && T$1(re);
    return t ? m$1.resolve(t) : Wn({ abortSignal: e }).then(ct);
  },
  (e) => {
    X(it, xo), ve(e);
  }
), Ho = w(re, Ae), ut = I(re, No[0], Ae); Ho("mount", Kn); const [, Lo, Jn] = Yn, [, er] = Xn, [tr, or] = No, [
  sr,
  nr,
  rr
] = b(
  (e) => m$1.fn(async (t) => {
    const o = at();
    o.available || Do();
    const s = await d(Ae, "biometry_auth_requested", {
      ...e,
      ...t,
      params: { reason: ((e || {}).reason || "").trim() }
    }), { token: n } = s;
    return typeof n == "string" && ve({ ...o, token: n }), s;
  }, e),
  "Biometry authentication is already in progress"
); ut("authenticate", sr); const [, Ro, ir] = nr, [, cr] = rr; Ho("openSettings", () => {
  i("web_app_biometry_open_settings");
}); const [
  lr,
  pr,
  dr
] = b(
  (e) => m$1.fn(async (t) => {
    const o = await d("web_app_biometry_request_access", it, {
      ...e,
      ...t,
      params: { reason: (e || {}).reason || "" }
    }).then(ct);
    return o.available || Do(), ve(o), o.accessGranted;
  }, e),
  "Biometry access request is already in progress"
); ut("requestAccess", lr); const [, jo, _r] = pr, [, fr] = dr;
function ve(e) {
  at.set(e), w$2(re, e);
}
ut(
  "updateToken",
  (e) => (e || (e = {}), d("web_app_biometry_update_token", "biometry_token_updated", {
    ...e,
    params: {
      token: e.token || "",
      reason: e.reason
    }
  }).then((t) => t.status))
);
function ye(e, t) {
  return we(e, { isMounted: t });
}
const V = we, Be = "closingBehavior", [ao] = /* @__PURE__ */ u(false), [Ke, Fo] = /* @__PURE__ */ u(false), Uo = ye(Be, Fo), Er = V(Be), Sr = Uo("disableConfirmation", () => {
  lt(false);
}), Cr = Uo("enableConfirmation", () => {
  lt(true);
}); Er("mount", () => {
  Ke() || (lt(
    c$1() && T$1(Be) || false
  ), Ke.set(true));
});
function lt(e) {
  e !== ao() && (i("web_app_setup_closing_behavior", { need_confirmation: e }), w$2(Be, e), ao.set(e));
}
const Go = "web_app_invoke_custom_method", de = w("cloudStorage", Go), zo = de("deleteItem", (e, t) => {
  const o = Array.isArray(e) ? e : [e];
  return o.length ? W("deleteStorageValues", { keys: o }, t).then() : m$1.resolve();
});
function Ar(e, t) {
  const o = Array.isArray(e) ? e : [e];
  return o.length ? W("getStorageValues", { keys: o }, t).then((s) => {
    const n = {
      // Fulfill the response with probably missing keys.
      ...o.reduce((r, a) => (r[a] = "", r), {}),
      ...parse(record(string(), string()), s)
    };
    return typeof e == "string" ? n[e] : n;
  }) : m$1.resolve(Array.isArray(e) ? {} : "");
}
const vr = de("getItem", Ar), Wo = de("getKeys", (e) => W("getStorageKeys", {}, e).then(
  (t) => parse(array(string()), t)
)), yr = de("setItem", (e, t, o) => W("saveStorageValue", {
  key: e,
  value: t
}, o).then()); de("clear", (e) => Wo(e).then(zo)); const me = "web_app_trigger_haptic_feedback", pt = w("hapticFeedback", me), Tr = pt(
  "impactOccurred",
  (e) => {
    i(me, {
      type: "impact",
      impact_style: e
    });
  }
), kr = pt(
  "notificationOccurred",
  (e) => {
    i(me, {
      type: "notification",
      notification_type: e
    });
  }
), Or = pt(
  "selectionChanged",
  () => {
    i(me, { type: "selection_change" });
  }
), [Qo] = /* @__PURE__ */ u(void 0);
function B(e) {
  return /* @__PURE__ */ c(() => {
    const t = Qo();
    return t ? t[e] : void 0;
  });
}
const Gr = B("user"), dt = "web_app_open_invoice", zr = w("invoice", dt);
function Qr(e, t, o) {
  let s;
  if (t === "url") {
    const { hostname: n, pathname: r } = new URL(e, window.location.href);
    if (n !== "t.me")
      throw new y(`Link has unexpected hostname: ${n}`);
    const a = r.match(/^\/(\$|invoice\/)([A-Za-z0-9\-_=]+)$/);
    if (!a)
      throw new y(
        'Expected to receive a link with a pathname in format "/invoice/{slug}" or "/${slug}"'
      );
    [, , s] = a;
  } else
    s = e, o = t;
  return d(dt, "invoice_closed", {
    ...o,
    params: { slug: s },
    capture: (n) => s === n.slug
  }).then((n) => n.status);
}
const [
  Kr,
  Yr,
  Xr
] = b(Qr, "Invoice is already opened"), Zr = zr("open", Kr), [, Jr, ea] = Yr, [, ta] = Xr, J = "locationManager", mt = "web_app_check_location", io = "web_app_open_location_settings", be = /* @__PURE__ */ z({
  available: false,
  accessGranted: false,
  accessRequested: false
});
function aa(e) {
  let t = false, o, s;
  return e.available && (t = true, o = e.access_requested, s = e.access_granted), {
    available: t,
    accessGranted: s || false,
    accessRequested: o || false
  };
}
const [
  ia,
  ca,
  ua,
  Xo
] = /* @__PURE__ */ pe(
  J,
  (e) => {
    const t = c$1() && T$1(J);
    return t ? m$1.resolve(t) : d("web_app_check_location", "location_checked", e).then(aa);
  },
  (e) => {
    be.set(e), w$2(J, e);
  }
), Zo = w(J, mt), la = I(J, Xo[0], mt); Zo("mount", ia); const [, da, ma] = ca, [, _a] = ua, [fa, ha] = Xo, [
  ba,
  ga,
  Ea
] = b(
  (e) => d("web_app_request_location", "location_requested", e).then((t) => {
    if (!t.available)
      throw be.set({ ...be(), available: false }), new ko("Location data tracking is not available");
    const { available: o, ...s } = t;
    return s;
  }),
  "Location request is currently in progress"
); la("requestLocation", ba); const [, Jo, Ca] = ga, [, wa] = Ea; Zo("openSettings", () => {
  i(io);
}, io);
function ft(e) {
  const t = {};
  for (const o in e) {
    const s = e[o];
    s !== void 0 && (t[o] = s);
  }
  return t;
}
const [Fe] = /* @__PURE__ */ u(false), [N, K] = /* @__PURE__ */ u({});
function h(e) {
  return /* @__PURE__ */ c(() => N()[e]);
}
const ht = h("button_color"), os = h("button_text_color"), ss = h("secondary_bg_color");
const ee = /* @__PURE__ */ z({
  hasShineEffect: false,
  isEnabled: true,
  isLoaderVisible: false,
  isVisible: false,
  text: "Continue"
}), bt = /* @__PURE__ */ c(() => {
  const e = ee();
  return {
    ...e,
    backgroundColor: e.backgroundColor || ht() || "#2481cc",
    textColor: e.textColor || os() || "#ffffff"
  };
}), [Ye, ns] = /* @__PURE__ */ u(false), Ga = "web_app_setup_main_button", rs = "main_button_pressed", Pe = "mainButton", gt = V(Pe), za = ye(Pe, ns); gt("mount", () => {
  if (!Ye()) {
    const e = c$1() && T$1(Pe);
    e && ee.set(e), Ye.set(true);
  }
}); gt(
  "onClick",
  (e) => X(rs, e)
); gt(
  "offClick",
  (e) => {
    me$1(rs, e);
  }
); za(
  "setParams",
  (e) => {
    ee.set({ ...ee(), ...ft(e) }), w$2(Pe, ee());
    const t = bt();
    t.text && i(Ga, {
      color: t.backgroundColor,
      has_shine_effect: t.hasShineEffect,
      is_active: t.isEnabled,
      is_progress_visible: t.isLoaderVisible,
      is_visible: t.isVisible,
      text: t.text,
      text_color: t.textColor
    });
  }
);
function Et(e, t) {
  document.documentElement.style.setProperty(e, t);
}
function St(e) {
  document.documentElement.style.removeProperty(e);
}
const G = "themeParams", Ct = "theme_changed", as = V(G), wt = ({ theme_params: e }) => {
  N.set(e), w$2(G, e);
}, [
  Za,
  is,
  Ja,
  cs
] = /* @__PURE__ */ pe(
  G,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  (e) => m$1.resolve(
    c$1() && T$1(G) || le().tgWebAppThemeParams || {}
  ),
  (e) => {
    X(Ct, wt), N.set(e);
  }
), ei = ye(G, cs[0]); ei(
  "bindCssVars",
  (e) => {
    if (Fe())
      throw new ot();
    e || (e = (s) => `--tg-theme-${k$1(s)}`);
    function t(s) {
      Object.entries(N()).forEach(([n, r]) => {
        r && s(n, r);
      });
    }
    function o() {
      t((s, n) => {
        Et(e(s), n);
      });
    }
    return o(), N.sub(o), Fe.set(true), () => {
      t(St), N.unsub(o), Fe.set(false);
    };
  }
); const us = as("mount", Za); is[2]; is[1]; Ja[1]; const [Xe, ni] = cs, ps = as("mountSync", () => {
  if (!Xe()) {
    const e = c$1() && T$1(G) || le().tgWebAppThemeParams || {};
    X(Ct, wt), m(() => {
      N.set(e), Xe.set(!0);
    });
  }
});
// @__NO_SIDE_EFFECTS__
function ds(e) {
  return /* @__PURE__ */ c(() => Te(e()));
}
function Te(e) {
  return H$2(e) ? e : K()[e];
}
const [ae] = /* @__PURE__ */ u("bg_color"), $t = /* @__PURE__ */ ds(ae), [ie] = /* @__PURE__ */ u("bottom_bar_bg_color"), Mt = /* @__PURE__ */ c(() => {
  const e = ie();
  return H$2(e) ? e : K()[e] || ss();
}), [ce] = /* @__PURE__ */ u("bg_color"), ms = /* @__PURE__ */ ds(ce), [Ue] = /* @__PURE__ */ u(false), [ke] = /* @__PURE__ */ u(true), _s = /* @__PURE__ */ c(() => ({
  backgroundColor: ae(),
  bottomBarColor: ie(),
  headerColor: ce(),
  isActive: ke()
})), ge = "web_app_set_background_color", Ee = "web_app_set_bottom_bar_color", D = "web_app_set_header_color", At = "visibility_changed", H = "miniApp", vt = {
  any: [
    ge,
    Ee,
    D
  ]
}, yt = (e) => {
  ke.set(e.is_visible), Ie();
}, Bt = (e) => {
  [
    [ce, D],
    [ae, ge],
    [ie, Ee]
  ].forEach(([t, o]) => {
    const s = t();
    if (!H$2(s) && // Header color setter uses additional checks. We don't apply changes if the current
    // value is a known color key because it updates automatically by itself.
    (o !== D || s !== "bg_color" && s !== "secondary_bg_color")) {
      const n = e[s];
      n && i(o, { color: n });
    }
  });
}, [
  mi,
  fs,
  _i,
  hs
] = /* @__PURE__ */ pe(
  H,
  (e) => us(e).then(() => c$1() && T$1(H) || void 0),
  (e) => {
    Pt.ifAvailable(e ? e.backgroundColor : "bg_color"), Tt.ifAvailable(e ? e.bottomBarColor : "bottom_bar_bg_color"), kt.ifAvailable(e ? e.headerColor : "bg_color"), ke.set(e ? e.isActive : true), X(At, yt), K.sub(Bt);
  }
), bs = V(H), gs = w(H, vt), Oe = I(H, hs[0], vt); Oe(
  "bindCssVars",
  (e) => {
    if (Ue())
      throw new ot();
    const [t, o] = L$2();
    function s(n, r) {
      function a() {
        Et(n, r() || null);
      }
      a(), t(r.sub(a), St.bind(null, n));
    }
    return e || (e = (n) => `--tg-${y$2(n)}`), s(e("bgColor"), $t), s(e("bottomBarColor"), Mt), s(e("headerColor"), ms), t(() => {
      Ue.set(false);
    }), Ue.set(true), o;
  }
); bs("close", (e) => {
  i("web_app_close", { return_back: e });
}); gs("mount", mi); fs[2]; fs[1]; _i[1]; const [Ze, Si] = hs; gs("mountSync", () => {
  if (!Ze()) {
    ps();
    const e = c$1() && T$1(H) || void 0;
    Pt.ifAvailable(e ? e.backgroundColor : "bg_color"), Tt.ifAvailable(e ? e.bottomBarColor : "bottom_bar_bg_color"), kt.ifAvailable(e ? e.headerColor : "bg_color"), X(At, yt), K.sub(Bt), m(() => {
      ke.set(e ? e.isActive : !0), Ze.set(!0);
    });
  }
}); bs("ready", () => {
  i("web_app_ready");
});
function Ie() {
  w$2(H, _s());
}
const Pt = Oe(
  "setBackgroundColor",
  (e) => {
    if (e === ae())
      return;
    const t = Te(e);
    if (!t)
      throw new st(e);
    i(ge, { color: t }), ae.set(e), Ie();
  },
  ge
), Tt = Oe(
  "setBottomBarColor",
  (e) => {
    if (e === ie())
      return;
    const t = Te(e);
    if (!t)
      throw new st(e);
    i(Ee, { color: t }), ie.set(e), Ie();
  },
  Ee
), kt = Oe(
  "setHeaderColor",
  (e) => {
    if (e !== ce()) {
      if (e === "bg_color" || e === "secondary_bg_color")
        i(D, { color_key: e });
      else {
        const t = Te(e);
        if (!t)
          throw new st(e);
        i(D, { color: t });
      }
      ce.set(e), Ie();
    }
  },
  D,
  {
    rgb: [D, "color", H$2]
  }
);
function Mi(e) {
  const t = e.message.trim(), o = (e.title || "").trim(), s = e.buttons || [];
  if (o.length > 64)
    throw new y(`Invalid title: ${o}`);
  if (!t || t.length > 256)
    throw new y(`Invalid message: ${t}`);
  if (s.length > 3)
    throw new y(`Invalid buttons count: ${s.length}`);
  return {
    title: o,
    message: t,
    buttons: s.length ? s.map((n, r) => {
      const a = n.id || "";
      if (a.length > 64)
        throw new y(`Button with index ${r} has invalid id: ${a}`);
      if (!n.type || n.type === "default" || n.type === "destructive") {
        const l = n.text.trim();
        if (!l || l.length > 64)
          throw new y(`Button with index ${r} has invalid text: ${l}`);
        return { type: n.type, text: l, id: a };
      }
      return { type: n.type, id: a };
    }) : [{ type: "close", id: "" }]
  };
}
const Ot = "web_app_open_popup", Ss = w("popup", Ot), [Cs, It, ws] = b(
  (e) => d(Ot, "popup_closed", {
    ...e,
    params: Mi(e)
  }).then(({ button_id: t }) => t === void 0 ? null : t),
  "A popup is already opened"
); Ss("open", Cs); It[1]; It[2]; ws[1]; const Ti = Ss("show", Cs), [, ki, Oi] = It, [, Ii] = ws, $s = "web_app_close_scan_qr_popup", Vt = "web_app_open_scan_qr_popup", Vi = "scan_qr_popup_closed", qi = "qr_text_received", Ms = w("qrScanner", Vt); Ms("close", () => {
  i($s), Q(As);
});
function Ni(e) {
  e || (e = {});
  const { onCaptured: t, text: o, capture: s } = e, [, n] = L$2(
    X(Vi, () => {
      r.resolve();
    }),
    X(qi, (a) => {
      t ? t(a.data) : (!s || s(a.data)) && (r.resolve(a.data), i($s));
    })
  ), r = new R$2(e);
  return (e.postEvent || i)(Vt, { text: o }), m$1.resolve(r).catch(qo).finally(n);
}
const [
  Hi,
  Li,
  Ri
] = b(Ni, "The QR Scanner is already opened"); Ms("open", Hi); const [, As, Fi] = Li, [, Ui] = Ri;
const te = /* @__PURE__ */ z({
  hasShineEffect: false,
  isEnabled: true,
  isLoaderVisible: false,
  isVisible: false,
  position: "left",
  text: "Cancel"
}), qt = /* @__PURE__ */ c(() => {
  const e = te();
  return {
    ...e,
    backgroundColor: e.backgroundColor || Mt() || "#000000",
    textColor: e.textColor || ht() || "#2481cc"
  };
}), [Je, vs] = /* @__PURE__ */ u(false), Ve = "web_app_setup_secondary_button", ys = "secondary_button_pressed", qe = "secondaryButton", xt = w(qe, Ve), Ji = I(qe, vs, Ve); xt("mount", () => {
  if (!Je()) {
    const e = c$1() && T$1(qe);
    e && te.set(e), Je.set(true);
  }
}); xt(
  "onClick",
  (e) => X(ys, e)
); xt(
  "offClick",
  (e) => {
    me$1(ys, e);
  }
); Ji(
  "setParams",
  (e) => {
    te.set({ ...te(), ...ft(e) }), w$2(qe, te());
    const t = qt();
    t.text && i(Ve, {
      color: t.backgroundColor,
      has_shine_effect: t.hasShineEffect,
      is_active: t.isEnabled,
      is_progress_visible: t.isLoaderVisible,
      is_visible: t.isVisible,
      position: t.position,
      text: t.text,
      text_color: t.textColor
    });
  }
);
const xe = "web_app_setup_settings_button", Bs = "settings_button_pressed", De = "settingsButton", [co] = /* @__PURE__ */ u(false), [Se] = /* @__PURE__ */ u(false), Dt = w(De, xe), Ps = I(De, Se, xe); Ps("hide", () => {
  Nt(false);
}); Dt("mount", () => {
  Se() || (Nt(c$1() && T$1(De) || false), Se.set(true));
});
function Nt(e) {
  e !== co() && (i(xe, { is_visible: e }), w$2(De, e), co.set(e));
}
Dt(
  "onClick",
  (e) => X(Bs, e)
); Dt(
  "offClick",
  (e) => {
    me$1(Bs, e);
  }
); Ps("show", () => {
  Nt(true);
});
const Ne = "web_app_setup_swipe_behavior", He = "swipeBehavior", [ue] = /* @__PURE__ */ u(false), [et] = /* @__PURE__ */ u(true), gc = w(He, Ne), Ts = I(He, ue, Ne), Ec = Ts("disableVertical", () => {
  Ht(false);
}), Sc = Ts("enableVertical", () => {
  Ht(true);
}); gc("mount", () => {
  ue() || (Ht(
    c$1() && T$1(He) || false,
    true
  ), ue.set(true));
});
function Ht(e, t) {
  (e !== et() || t) && (i(Ne, { allow_vertical_swipe: e }), w$2(He, e), et.set(e));
}
const j = "viewport", Lt = "fullscreen_changed", Rt = "safe_area_changed", jt = "content_safe_area_changed", Ft = "viewport_changed", ks = V(j), uo = { left: 0, top: 0, bottom: 0, right: 0 };
function Ge(e) {
  return Math.max(e, 0);
}
const [ze, Os] = /* @__PURE__ */ u({
  contentSafeAreaInsets: uo,
  height: 0,
  isExpanded: false,
  isFullscreen: false,
  safeAreaInsets: uo,
  stableHeight: 0,
  width: 0
});
function F(e) {
  return /* @__PURE__ */ c(() => Os()[e]);
}
const Ut = F("height"), Gt = F("stableHeight"), Is = F("width"), $c = F("isExpanded");
function Y(e) {
  const { height: t, stableHeight: o, width: s } = e;
  ze.set({
    ...ze(),
    ...ft({
      ...e,
      height: t ? Ge(t) : void 0,
      width: s ? Ge(s) : void 0,
      stableHeight: o ? Ge(o) : void 0
    })
  }), w$2(j, ze());
}
function Ac() {
  return T$1(j);
}
function Le(e) {
  return /* @__PURE__ */ c(() => zt()[e]);
}
const zt = F("contentSafeAreaInsets"), Vs = Le("bottom"), qs = Le("left"), xs = Le("right"), Ds = Le("top");
function Re(e) {
  return /* @__PURE__ */ c(() => Wt()[e]);
}
const Wt = F("safeAreaInsets"), Ns = Re("bottom"), Hs = Re("left"), Ls = Re("right"), Rs = Re("top"), js = "web_app_request_safe_area", Fs = w(j, js), lo = Fs(
  "requestContentSafeAreaInsets",
  (e) => d("web_app_request_content_safe_area", jt, e)
);
function vc(e) {
  return d("web_app_request_viewport", Ft, e);
}
const po = Fs(
  "requestSafeAreaInsets",
  (e) => d(js, Rt, e)
), Us = (e) => {
  const { height: t } = e;
  Y({
    isExpanded: e.is_expanded,
    height: t,
    width: e.width,
    stableHeight: e.is_state_stable ? t : void 0
  });
}, Gs = (e) => {
  Y({ isFullscreen: e.is_fullscreen });
}, zs = (e) => {
  Y({ safeAreaInsets: e });
}, Ws = (e) => {
  Y({ contentSafeAreaInsets: e });
}, [
  yc,
  Bc,
  Pc,
  Tc
] = /* @__PURE__ */ pe(
  j,
  (e) => {
    const t = c$1() && Ac();
    return t ? m$1.resolve(t) : m$1.fn(async (o) => {
      const s = await m$1.all([
        po.isAvailable() ? po(o) : Wt(),
        lo.isAvailable() ? lo(o) : zt()
      ]), n = le(), r = {
        contentSafeAreaInsets: s[1],
        isFullscreen: !!n.tgWebAppFullscreen,
        safeAreaInsets: s[0]
      };
      if (["macos", "tdesktop", "unigram", "webk", "weba", "web"].includes(n.tgWebAppPlatform)) {
        const a = window;
        return {
          ...r,
          height: a.innerHeight,
          isExpanded: true,
          stableHeight: a.innerHeight,
          width: a.innerWidth
        };
      }
      return vc(o).then((a) => ({
        ...r,
        height: a.height,
        isExpanded: a.is_expanded,
        stableHeight: a.is_state_stable ? a.height : 0,
        width: a.width
      }));
    }, e);
  },
  (e) => {
    X(Ft, Us), X(Lt, Gs), X(Rt, zs), X(jt, Ws), Y(e);
  }
); ks("mount", yc); const [, Qs, Oc] = Bc, [, Ic] = Pc, [Qt, Vc] = Tc;
const xc = ye(j, Qt), [We] = /* @__PURE__ */ u(false); xc(
  "bindCssVars",
  (e) => {
    if (We())
      throw new ot();
    e || (e = (o) => `--tg-viewport-${y$2(o)}`);
    const t = [
      ["height", Ut],
      ["stableHeight", Gt],
      ["width", Is],
      ["safeAreaInsetTop", Rs],
      ["safeAreaInsetBottom", Ns],
      ["safeAreaInsetLeft", Hs],
      ["safeAreaInsetRight", Ls],
      ["contentSafeAreaInsetTop", Ds],
      ["contentSafeAreaInsetBottom", Vs],
      ["contentSafeAreaInsetLeft", qs],
      ["contentSafeAreaInsetRight", xs]
    ].reduce((o, [s, n]) => {
      const r = e(s);
      if (r) {
        const a = () => {
          Et(r, `${n()}px`);
        };
        o.push([a, n.sub(a), r]);
      }
      return o;
    }, []);
    return t.forEach((o) => {
      o[0]();
    }), We.set(true), () => {
      t.forEach((o) => {
        o[1](), St(o[2]);
      }), We.set(false);
    };
  }
); const Hc = ks("expand", () => {
  i("web_app_expand");
}), Ks = "web_app_request_fullscreen", Lc = I(j, Qt, Ks), Ys = F("isFullscreen"), [
  Rc] = /* @__PURE__ */ u(), [
  Fc] = /* @__PURE__ */ u();
function Xs(e, t) {
  return Lc(
    e,
    b(
      (o) => d(
        t ? Ks : "web_app_exit_fullscreen",
        [Lt, "fullscreen_failed"],
        o
      ).then((s) => {
        if ("error" in s && s.error !== "ALREADY_FULLSCREEN")
          throw new Vn(s.error);
        const n = "is_fullscreen" in s ? s.is_fullscreen : true;
        n !== Ys() && Y({ isFullscreen: n });
      }),
      "Fullscreen mode change is already being requested",
      {
        promise: Rc,
        error: Fc
      }
    )[0]
  );
}
const Gc = Xs("requestFullscreen", true), zc = Xs("exitFullscreen"), Zs = "web_app_request_emoji_status_access", [
  Wc,
  Qc,
  Kc
] = b((e) => d(Zs, "emoji_status_access_requested", e).then((t) => t.status), "Emoji status access request is already in progress"), [, il, cl] = Qc, [, ul] = Kc, Js = "web_app_set_emoji_status", [
  Yc,
  Xc,
  Zc
] = b(
  (e, t) => d(Js, ["emoji_status_set", "emoji_status_failed"], {
    params: {
      custom_emoji_id: e,
      duration: (t || {}).duration
    },
    ...t
  }).then((o) => {
    if (o && "error" in o)
      throw new In(o.error);
  }),
  "Emoji status set request is currently in progress"
), [, pl, dl] = Xc, [, ml] = Zc, sn = "web_app_check_home_screen", [
  eu,
  tu,
  ou
] = b((e) => d(sn, "home_screen_checked", e).then((t) => t.status || "unknown"), "Check home screen status request is currently in progress"), [, Sl, Cl] = tu, [, wl] = ou, su = V(), $l = su(
  "openLink",
  (e, t) => {
    if (typeof e == "string")
      try {
        e = new URL(e);
      } catch (o) {
        throw new y(`"${e.toString()}" is invalid URL`, o);
      }
    t || (t = {}), i("web_app_open_link", {
      url: e.toString(),
      try_browser: t.tryBrowser,
      try_instant_view: t.tryInstantView
    });
  }
), _o = "web_app_open_tg_link", nu = V(), ru = nu(
  "openTelegramLink",
  (e) => {
    const t = e.toString();
    if (!t.match(/^https:\/\/t.me\/.+/))
      throw new y(`"${t}" is invalid URL`);
    if (!z$1(_o, O())) {
      window.location.href = t;
      return;
    }
    e = new URL(e), i(_o, { path_full: e.pathname + e.search });
  }
), au = V(), Ml = au(
  "shareURL",
  (e, t) => {
    ru(
      "https://t.me/share/url?" + new URLSearchParams({ url: e, text: t || "" }).toString().replace(/\+/g, "%20")
    );
  }
);
function iu(e, t) {
  return new m$1({ abortSignal: t, timeout: e }).catch(() => {
  });
}
const nn = "web_app_request_phone", [
  cu,
  uu,
  lu
] = b((e) => d(nn, "phone_requested", e).then((t) => t.status), "Phone access request is currently in progress"), pu = /* @__PURE__ */ p("requestPhoneAccess", cu, {
  isSupported: nn
}), [, Al, vl] = uu, [, yl] = lu;
async function fo(e) {
  const t = parse(string(), await W("getRequestedContact", {}, {
    ...e,
    timeout: (e || {}).timeout || 5e3
  }));
  return {
    raw: t,
    parsed: parse(
      pipe(
        // todo: Union is unnecessary here, but we use it to comply TypeScript checker.
        union([string(), instance(URLSearchParams)]),
        ce$1(
          looseObject({
            contact: pipe(
              string(),
              oe(),
              looseObject({
                user_id: number(),
                phone_number: string(),
                first_name: string(),
                last_name: optional(string())
              })
            ),
            auth_date: pipe(
              string(),
              transform((o) => new Date(Number(o) * 1e3)),
              date()
            ),
            hash: string()
          })
        )
      ),
      t
    )
  };
}
const [du, mu, _u] = b(
  (e) => new m$1(
    async (t, o, s) => {
      try {
        return t(await fo(s));
      } catch (a) {
        if (a instanceof ValiError)
          throw a;
      }
      if (await pu(s) !== "sent")
        throw new Oo("User denied access");
      let r = 50;
      for (; !s.isAborted(); ) {
        try {
          return t(await fo(s));
        } catch (a) {
          if (a instanceof ValiError)
            throw a;
        }
        await iu(r), r += 50;
      }
    },
    e
  ),
  "Contact is already being requested"
), [, Pl, Tl] = mu, [, kl] = _u, an = "web_app_request_write_access", [
  hu,
  bu,
  gu
] = b(
  (e) => d(an, "write_access_requested", e).then((t) => t.status),
  "Write access request is currently in progress"
), [, Il, Vl] = bu, [, ql] = gu;
const bo = "web_app_hide_keyboard", Hl = /* @__PURE__ */ p(
  "hideKeyboard",
  () => i(bo),
  { isSupported: bo }
);

function s(r, t) {
  return reactExports.useSyncExternalStore(
    (n) => r.sub(n),
    r,
    r
  );
}

export { $c as $, Be$1 as B, Cr as C, Ec as E, Fn as F, Gc as G, Hc as H, K, Ml as M, Or as O, Rn as R, Se$1 as S, Tt as T, Ut as U, Wt as W, Ys as Y, Zr as Z, Sc as a, zt as b, Gt as c, Hl as d, Sr as e, $l as f, Wo as g, zo as h, Ti as i, kr as j, kt as k, Tr as l, Hn as m, jn as n, Gr as o, ru as r, s, vr as v, xn as x, yr as y, zc as z };
