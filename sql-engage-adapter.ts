/**
 * SQL-Engage Three-Layer Concept Mapping Adapter
 * 
 * This TypeScript module provides integration between the SQL-Engage
 * error detection system and the ALGL educational content pipeline.
 * 
 * Layer 1: Error Subtype Detection (sql-engage.ts)
 * Layer 2: Alignment Map (error → concept IDs)
 * Layer 3: Concept Registry (concept → textbook content)
 */

// Layer 1: Error Subtype Types
export interface ErrorSubtype {
  id: number;
  name: string;
  severity: 'error' | 'warning' | 'info';
  category: 'syntax' | 'logic' | 'completeness';
}

export interface ErrorSubtypesManifest {
  schemaVersion: string;
  description: string;
  createdAt: string;
  totalSubtypes: number;
  subtypes: Record<string, ErrorSubtype>;
}

// Layer 2: Alignment Map Types
export interface AlignmentMapping {
  error_subtype_id: number;
  concept_ids: string[];
  confidence: 'verified' | 'high' | 'medium' | 'low';
  teaching_strategy: string;
  remediation_order: string[];
}

export interface AlignmentMapManifest {
  schemaVersion: string;
  description: string;
  createdAt: string;
  totalMappings: number;
  mappings: Record<string, AlignmentMapping>;
}

// Layer 3: Concept Registry Types
export interface ConceptInfo {
  id: string;
  title: string;
  description: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  estimatedReadTime: number;
  category: string;
  contentLocation: string;
  qualityStatus: 'verified' | 'draft' | 'deprecated';
  learningObjectives: string[];
}

export interface ConceptRegistryManifest {
  schemaVersion: string;
  description: string;
  createdAt: string;
  totalConcepts: number;
  concepts: Record<string, ConceptInfo>;
  statistics: {
    byDifficulty: Record<string, number>;
    byCategory: Record<string, number>;
    totalPracticeProblems: number;
    coverageByStatus: Record<string, number>;
  };
  learningPaths: Record<string, string[]>;
}

// Complete Learning Path
export interface LearningPath {
  errorSubtype: string;
  errorInfo: ErrorSubtype;
  teachingStrategy: string | null;
  concepts: ConceptInfo[];
  totalReadTime: number;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
}

/**
 * Three-Layer Concept Mapping System
 * 
 * Usage:
 *   const mapper = new ConceptMappingSystem(
 *     errorSubtypesJson,
 *     alignmentMapJson,
 *     conceptRegistryJson
 *   );
 *   
 *   // Layer 1→2: Get concepts for error
 *   const concepts = mapper.getConceptsForError('missing_comma_in_select');
 *   
 *   // Layer 2→3: Get content for concept
 *   const content = mapper.getConceptContent('select-basic');
 *   
 *   // Layer 1→2→3: Get complete learning path
 *   const path = mapper.getLearningPath('missing_comma_in_select');
 */
export class ConceptMappingSystem {
  private errorSubtypes: ErrorSubtypesManifest;
  private alignmentMap: AlignmentMapManifest;
  private conceptRegistry: ConceptRegistryManifest;

  constructor(
    errorSubtypes: ErrorSubtypesManifest,
    alignmentMap: AlignmentMapManifest,
    conceptRegistry: ConceptRegistryManifest
  ) {
    this.errorSubtypes = errorSubtypes;
    this.alignmentMap = alignmentMap;
    this.conceptRegistry = conceptRegistry;
  }

  // Layer 1: Error Subtype Methods
  
  /**
   * Get error subtype information
   */
  getErrorInfo(errorSubtype: string): ErrorSubtype | null {
    return this.errorSubtypes.subtypes[errorSubtype] || null;
  }

  /**
   * List all error subtypes
   */
  listErrorSubtypes(): string[] {
    return Object.keys(this.errorSubtypes.subtypes);
  }

  /**
   * Detect error subtype from error message and SQL code
   */
  detectErrorSubtype(errorMessage: string, sqlCode: string): string | null {
    const errorLower = errorMessage.toLowerCase();
    
    // Pattern matching for common errors
    const patterns: Record<string, RegExp[]> = {
      missing_comma_in_select: [
        /near ".*": syntax error/i,
        /missing comma/i,
        /syntax error at or near "FROM"/i
      ],
      extra_comma_in_select: [
        /near "\)": syntax error/i
      ],
      missing_where_clause: [
        /where clause/i
      ],
      missing_join_condition: [
        /join.*condition/i,
        /on clause/i
      ],
      missing_group_by: [
        /group by/i,
        /must appear in the group by/i
      ],
      ambiguous_column_reference: [
        /ambiguous column/i,
        /ambiguous attribute/i
      ],
      incorrect_null_comparison: [
        /null/i,
        /operator does not exist/i
      ]
    };

    for (const [subtype, regexPatterns] of Object.entries(patterns)) {
      for (const pattern of regexPatterns) {
        if (pattern.test(errorLower)) {
          return subtype;
        }
      }
    }

    return null;
  }

  // Layer 2: Alignment Map Methods

  /**
   * Get concept IDs for an error subtype (Layer 1→2)
   */
  getConceptsForError(errorSubtype: string): string[] {
    const mapping = this.alignmentMap.mappings[errorSubtype];
    if (!mapping) return [];

    // Filter by confidence
    const confidence = mapping.confidence;
    if (['high', 'verified', 'medium'].includes(confidence)) {
      return mapping.concept_ids;
    }

    return [];
  }

  /**
   * Get recommended learning order for error remediation
   */
  getRemediationOrder(errorSubtype: string): string[] {
    const mapping = this.alignmentMap.mappings[errorSubtype];
    if (mapping) {
      return mapping.remediation_order || mapping.concept_ids;
    }
    return [];
  }

  /**
   * Get teaching strategy for error
   */
  getTeachingStrategy(errorSubtype: string): string | null {
    const mapping = this.alignmentMap.mappings[errorSubtype];
    return mapping?.teaching_strategy || null;
  }

  // Layer 3: Concept Content Methods

  /**
   * Get content for a concept (Layer 2→3)
   */
  getConceptContent(conceptId: string): ConceptInfo | null {
    return this.conceptRegistry.concepts[conceptId] || null;
  }

  /**
   * List all concept IDs
   */
  listConcepts(): string[] {
    return Object.keys(this.conceptRegistry.concepts);
  }

  /**
   * Get concepts by difficulty
   */
  getConceptsByDifficulty(
    difficulty: 'beginner' | 'intermediate' | 'advanced'
  ): ConceptInfo[] {
    return Object.values(this.conceptRegistry.concepts).filter(
      c => c.difficulty === difficulty
    );
  }

  /**
   * Get concepts by category
   */
  getConceptsByCategory(category: string): ConceptInfo[] {
    return Object.values(this.conceptRegistry.concepts).filter(
      c => c.category === category
    );
  }

  // Cross-Layer Methods

  /**
   * Get complete learning path from error to content (Layer 1→2→3)
   */
  getLearningPath(errorSubtype: string): LearningPath | null {
    // Layer 1: Error info
    const errorInfo = this.getErrorInfo(errorSubtype);
    if (!errorInfo) return null;

    // Layer 2: Alignment
    const conceptIds = this.getRemediationOrder(errorSubtype);
    const teachingStrategy = this.getTeachingStrategy(errorSubtype);

    // Layer 3: Content
    const concepts = conceptIds
      .map(id => this.getConceptContent(id))
      .filter((c): c is ConceptInfo => c !== null);

    // Calculate path difficulty
    const difficulty = this.calculatePathDifficulty(concepts);

    return {
      errorSubtype,
      errorInfo,
      teachingStrategy,
      concepts,
      totalReadTime: concepts.reduce((sum, c) => sum + c.estimatedReadTime, 0),
      difficulty
    };
  }

  private calculatePathDifficulty(
    concepts: ConceptInfo[]
  ): 'beginner' | 'intermediate' | 'advanced' {
    if (concepts.length === 0) return 'beginner';

    const difficulties = concepts.map(c => c.difficulty);
    if (difficulties.includes('advanced')) return 'advanced';
    if (difficulties.includes('intermediate')) return 'intermediate';
    return 'beginner';
  }

  /**
   * Search concepts by keyword
   */
  searchConcepts(query: string): ConceptInfo[] {
    const queryLower = query.toLowerCase();
    
    return Object.values(this.conceptRegistry.concepts).filter(concept => {
      // Search title and description
      if (concept.title.toLowerCase().includes(queryLower) ||
          concept.description.toLowerCase().includes(queryLower)) {
        return true;
      }
      // Search learning objectives
      if (concept.learningObjectives.some(obj => 
        obj.toLowerCase().includes(queryLower)
      )) {
        return true;
      }
      return false;
    });
  }

  // Utility Methods

  /**
   * Get statistics about the mapping system
   */
  getStatistics(): {
    totalErrors: number;
    totalConcepts: number;
    totalMappings: number;
    coverageByDifficulty: Record<string, number>;
  } {
    return {
      totalErrors: this.errorSubtypes.totalSubtypes,
      totalConcepts: this.conceptRegistry.totalConcepts,
      totalMappings: this.alignmentMap.totalMappings,
      coverageByDifficulty: this.conceptRegistry.statistics.byDifficulty
    };
  }

  /**
   * Validate mapping completeness
   */
  validateMapping(): {
    isValid: boolean;
    missingConcepts: string[];
    unmappedErrors: string[];
  } {
    const missingConcepts: string[] = [];
    const unmappedErrors: string[] = [];

    // Check all mappings have valid concepts
    for (const [errorSubtype, mapping] of Object.entries(this.alignmentMap.mappings)) {
      for (const conceptId of mapping.concept_ids) {
        if (!this.conceptRegistry.concepts[conceptId]) {
          missingConcepts.push(`${errorSubtype} -> ${conceptId}`);
        }
      }
    }

    // Check all error subtypes have mappings
    for (const errorSubtype of Object.keys(this.errorSubtypes.subtypes)) {
      if (!this.alignmentMap.mappings[errorSubtype]) {
        unmappedErrors.push(errorSubtype);
      }
    }

    return {
      isValid: missingConcepts.length === 0 && unmappedErrors.length === 0,
      missingConcepts,
      unmappedErrors
    };
  }
}

/**
 * Create ConceptMappingSystem from JSON files
 */
export function createConceptMappingSystem(
  errorSubtypesJson: ErrorSubtypesManifest,
  alignmentMapJson: AlignmentMapManifest,
  conceptRegistryJson: ConceptRegistryManifest
): ConceptMappingSystem {
  return new ConceptMappingSystem(
    errorSubtypesJson,
    alignmentMapJson,
    conceptRegistryJson
  );
}

/**
 * Teaching strategies for different error types
 */
export const TEACHING_STRATEGIES: Record<string, {
  name: string;
  description: string;
  approach: string;
}> = {
  start_fundamentals: {
    name: "Start with Fundamentals",
    description: "Begin with basic SQL concepts",
    approach: "Introduce SELECT syntax and structure first"
  },
  select_mastery: {
    name: "SELECT Mastery",
    description: "Focus on SELECT statement details",
    approach: "Practice column selection and DISTINCT"
  },
  syntax_drill: {
    name: "Syntax Drill",
    description: "Repetitive practice of correct syntax",
    approach: "Multiple exercises on comma placement"
  },
  filtering_basics: {
    name: "Filtering Basics",
    description: "Learn WHERE clause fundamentals",
    approach: "Start with simple conditions"
  },
  operator_mastery: {
    name: "Operator Mastery",
    description: "Master logical and comparison operators",
    approach: "Practice AND, OR, NOT combinations"
  },
  join_types: {
    name: "JOIN Types",
    description: "Understand different JOIN operations",
    approach: "Visual explanations of JOIN types"
  },
  join_conditions: {
    name: "JOIN Conditions",
    description: "Learn ON clause syntax",
    approach: "Practice table relationships"
  },
  group_by_mastery: {
    name: "GROUP BY Mastery",
    description: "Master aggregation and grouping",
    approach: "Understand column requirements"
  },
  set_operations: {
    name: "Set Operations",
    description: "Learn UNION and related operations",
    approach: "Practice combining result sets"
  },
  subquery_basics: {
    name: "Subquery Basics",
    description: "Introduction to nested queries",
    approach: "Start with simple IN subqueries"
  },
  aliasing: {
    name: "Aliasing",
    description: "Learn table and column aliases",
    approach: "Practice disambiguation"
  }
};

// Export default for easy importing
export default ConceptMappingSystem;
