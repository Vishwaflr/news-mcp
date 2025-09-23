function analysisControl() {
    return {
        // Selection Mode System
        selectionMode: 'timeRange', // 'latest', 'timeRange', 'unanalyzed'

        // Selection Parameters
        latestCount: 50,
        timeRangeDays: 7,
        timeRangeHours: 0,

        // Active Selection State
        activeSelection: {
            mode: null,
            params: {},
            description: ''
        },

        // Additive Filters
        filters: {
            useFeedFilter: false,
            feed_id: '',
            unanalyzed_only: false,
            override_existing: false
        },

        // Analysis Parameters
        params: {
            model_tag: 'gpt-4.1-nano',
            rate_per_second: 1.0,
            limit: 200
        },
        defaultParams: {
            model_tag: 'gpt-4.1-nano',
            rate_per_second: 1.0,
            limit: 200
        },
        preview: {
            item_count: 0,
            estimated_cost_usd: 0,
            estimated_duration_minutes: 0
        },

        // UI State
        loading: false,

        init() {
            this.loadDefaultParams();
            this.updatePreview();
        },

        // Selection Mode Functions
        setLatestSelection() {
            this.activeSelection = {
                mode: 'latest',
                params: { count: this.latestCount },
                description: `Latest ${this.latestCount} articles`
            };
            console.log('Set Latest Selection:', this.activeSelection);
            this.updatePreview();
        },

        setTimeRangeSelection() {
            const totalHours = (this.timeRangeDays * 24) + parseInt(this.timeRangeHours);
            let description = '';

            if (this.timeRangeDays > 0 && this.timeRangeHours > 0) {
                description = `Last ${this.timeRangeDays} days and ${this.timeRangeHours} hours`;
            } else if (this.timeRangeDays > 0) {
                description = `Last ${this.timeRangeDays} day${this.timeRangeDays > 1 ? 's' : ''}`;
            } else if (this.timeRangeHours > 0) {
                description = `Last ${this.timeRangeHours} hour${this.timeRangeHours > 1 ? 's' : ''}`;
            } else {
                description = 'All time';
            }

            this.activeSelection = {
                mode: 'timeRange',
                params: {
                    days: this.timeRangeDays,
                    hours: this.timeRangeHours,
                    totalHours: totalHours
                },
                description: description
            };
            console.log('Set Time Range Selection:', this.activeSelection);
            this.updatePreview();
        },

        setUnanalyzedSelection() {
            this.activeSelection = {
                mode: 'unanalyzed',
                params: {},
                description: 'All unanalyzed articles'
            };
            console.log('Set Unanalyzed Selection:', this.activeSelection);
            this.updatePreview();
        },

        clearSelection() {
            this.activeSelection = {
                mode: null,
                params: {},
                description: ''
            };
            this.selectionMode = 'timeRange'; // Reset to default
            console.log('Selection cleared');
            this.updatePreview();
        },

        setTimeRange(range) {
            console.log(`Set time range: ${range}`);
            this.updatePreview();
        },

        async updatePreview() {
            try {
                // If no active selection, clear preview
                if (!this.activeSelection.mode) {
                    this.preview = {
                        total_items: 0,
                        analyzed_items: 0,
                        item_count: 0,
                        estimated_cost_usd: 0,
                        estimated_duration_minutes: 0
                    };
                    return;
                }

                // Build the scope object for the API
                const scope = {
                    type: "global",
                    feed_ids: [],
                    item_ids: [],
                    unanalyzed_only: !this.filters.override_existing
                };

                // Configure scope based on selection mode
                if (this.activeSelection.mode === 'latest') {
                    scope.type = "global";
                } else if (this.activeSelection.mode === 'timeRange') {
                    scope.type = "timerange";
                    if (this.activeSelection.params.totalHours) {
                        const endTime = new Date();
                        const startTime = new Date(endTime.getTime() - (this.activeSelection.params.totalHours * 60 * 60 * 1000));
                        scope.start_time = startTime.toISOString();
                        scope.end_time = endTime.toISOString();
                    }
                } else if (this.activeSelection.mode === 'unanalyzed') {
                    scope.type = "global";
                    scope.unanalyzed_only = true;
                }

                // Add feed filter if specified
                if (this.filters.useFeedFilter && this.filters.feed_id) {
                    scope.feed_ids = [parseInt(this.filters.feed_id)];
                    scope.type = "feeds";
                }

                // Build params
                const params = {
                    model_tag: this.params.model_tag,
                    rate_per_second: this.params.rate_per_second,
                    limit: this.activeSelection.params.count || 50,
                    override_existing: this.filters.override_existing || false,
                    newest_first: true
                };

                // Call the preview API
                const response = await fetch('/api/analysis/preview', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ scope, params })
                });

                if (!response.ok) {
                    console.error('Preview API failed:', response.statusText);
                    // Fallback to estimate
                    this.estimatePreview();
                    return;
                }

                const previewData = await response.json();

                // Update preview with actual data from API
                this.preview = {
                    total_items: previewData.total_items || 0,
                    analyzed_items: previewData.already_analyzed || 0,
                    item_count: previewData.item_count || 0,
                    estimated_cost_usd: previewData.estimated_cost_usd || 0,
                    estimated_duration_minutes: previewData.estimated_duration_minutes || 0
                };

                console.log('Preview updated from API:', this.preview);
            } catch (error) {
                console.error('Preview update failed:', error);
                // Fallback to estimate
                this.estimatePreview();
            }
        },

        estimatePreview() {
            // Fallback estimation logic (old code)
            let totalItems = 0;
            let analyzedItems = 0;

            if (this.activeSelection.mode === 'latest') {
                totalItems = this.activeSelection.params.count || 50;
                analyzedItems = Math.floor(totalItems * 0.3); // More realistic: 30% analyzed
            } else if (this.activeSelection.mode === 'timeRange') {
                const totalHours = this.activeSelection.params.totalHours || 24;
                totalItems = Math.min(totalHours * 10, 1000);
                analyzedItems = Math.floor(totalItems * 0.3);
            } else if (this.activeSelection.mode === 'unanalyzed') {
                totalItems = 500;
                analyzedItems = 0;
            }

            if (this.filters.useFeedFilter && this.filters.feed_id) {
                totalItems = Math.floor(totalItems * 0.3);
                analyzedItems = Math.floor(analyzedItems * 0.3);
            }

            let itemsToAnalyze = this.filters.override_existing ?
                totalItems : (totalItems - analyzedItems);

            this.preview = {
                total_items: totalItems,
                analyzed_items: analyzedItems,
                item_count: itemsToAnalyze,
                estimated_cost_usd: itemsToAnalyze * 0.0003,
                estimated_duration_minutes: Math.ceil(itemsToAnalyze / (this.params.rate_per_second * 60))
            };
        },

        buildQuery() {
            if (!this.activeSelection.mode) {
                return null; // No selection active
            }

            let query = {
                selection_mode: this.activeSelection.mode,
                ...this.activeSelection.params
            };

            // Add additive filters
            if (this.filters.useFeedFilter && this.filters.feed_id) {
                query.feed_id = this.filters.feed_id;
            }

            if (this.filters.unanalyzed_only) {
                query.unanalyzed_only = true;
            }

            if (this.filters.override_existing) {
                query.override_existing = true;
            }

            return query;
        },

        async startRun() {
            try {
                const query = this.buildQuery();
                if (!query) {
                    alert('Please select a target article selection first by clicking a SET button.');
                    return;
                }

                console.log('Starting analysis run with query:', query);

                // Build RunScope - map frontend modes to backend scope types
                const scope = {
                    type: "global",  // Default to global scope
                    feed_ids: [],
                    item_ids: [],
                    article_ids: [],
                    start_time: null,
                    end_time: null,
                    unanalyzed_only: true,  // Default to unanalyzed only
                    model_tag_not_current: false,
                    min_impact_threshold: null,
                    max_impact_threshold: null
                };

                // Map frontend selection modes to backend scope
                if (query.selection_mode === 'latest') {
                    // Latest articles - use global scope with limit in params
                    scope.type = "global";
                } else if (query.selection_mode === 'timeRange') {
                    // Time range - use timerange scope
                    scope.type = "timerange";
                    if (query.totalHours) {
                        const endTime = new Date();
                        const startTime = new Date(endTime.getTime() - (query.totalHours * 60 * 60 * 1000));
                        scope.start_time = startTime.toISOString();
                        scope.end_time = endTime.toISOString();
                    }
                } else if (query.selection_mode === 'unanalyzed') {
                    // Unanalyzed only - use global scope with unanalyzed_only filter
                    scope.type = "global";
                    scope.unanalyzed_only = true;
                }

                // Add feed filter if specified
                if (query.feed_id) {
                    scope.feed_ids = [parseInt(query.feed_id)];
                    scope.type = "feeds";  // Change to feeds scope when feed filter is used
                }

                // Override unanalyzed_only filter if specified
                if (query.hasOwnProperty('unanalyzed_only')) {
                    scope.unanalyzed_only = query.unanalyzed_only;
                }

                const params = {
                    model_tag: this.params.model_tag,
                    rate_per_second: this.params.rate_per_second,
                    limit: query.count || this.params.limit || 1000,  // Use count from query or default
                    override_existing: query.override_existing || false,
                    newest_first: true,
                    retry_failed: true,
                    dry_run: false,
                    triggered_by: "manual"
                };

                const payload = { scope, params };
                console.log('API payload:', payload);

                // Show loading state
                this.loading = true;
                const response = await fetch('/api/analysis/runs', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();
                console.log('Analysis run started:', result);

                // Success feedback
                alert(`Analysis run started successfully!\nRun ID: ${result.id}\nSelection: ${this.activeSelection.description}\nEstimated items: ${this.preview.item_count}`);

                // Clear the selection
                this.clearSelection();

                // Refresh active runs
                this.refreshActiveRuns();

            } catch (error) {
                console.error('Failed to start run:', error);
                alert('Failed to start run: ' + error.message);
            } finally {
                this.loading = false;
            }
        },

        async loadDefaultParams() {
            try {
                const response = await fetch('/api/analysis/presets?default=true');
                if (response.ok) {
                    const presets = await response.json();
                    const defaultPreset = presets.find(p => p.is_default);
                    if (defaultPreset) {
                        this.params.model_tag = defaultPreset.model_tag;
                        this.params.rate_per_second = defaultPreset.rate_per_second;
                        console.log('Loaded default parameters:', defaultPreset);
                    }
                }
            } catch (error) {
                console.error('Failed to load default parameters:', error);
            }
        },

        async saveDefaultParams() {
            try {
                const preset = {
                    name: 'Default Settings',
                    model_tag: this.params.model_tag,
                    rate_per_second: this.params.rate_per_second,
                    is_default: true
                };

                const response = await fetch('/api/analysis/presets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(preset)
                });

                if (response.ok) {
                    alert('Default parameters saved successfully!');
                } else {
                    throw new Error('Failed to save preset');
                }
            } catch (error) {
                console.error('Failed to save parameters:', error);
                alert('Failed to save parameters: ' + error.message);
            }
        },

        async refreshActiveRuns() {
            try {
                const response = await fetch('/api/analysis/runs?active_only=true');
                if (response.ok) {
                    const activeRuns = await response.json();
                    // Update active runs display via HTMX - only if element exists
                    const container = document.getElementById('active-runs-container');
                    if (container && typeof htmx !== 'undefined') {
                        htmx.trigger(container, 'refresh-runs');
                    }
                    console.log('Active runs refreshed:', activeRuns.length);
                }
            } catch (error) {
                console.error('Failed to refresh active runs:', error);
            }
        }
    }
}
