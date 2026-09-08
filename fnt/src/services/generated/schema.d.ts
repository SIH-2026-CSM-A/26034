export interface paths {
    "/auth/token": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Issue Access Token
         * @description Exchange officer credentials for an access token.
         */
        post: operations["issue_access_token_auth_token_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/scans": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Scans
         * @description Scans this officer may see, narrowed by the supplied filters and by nothing else.
         *
         *     The jurisdiction predicate is applied by the repository on every query and is not
         *     something a caller can widen — there is no jurisdiction parameter on this route.
         */
        get: operations["list_scans_scans_get"];
        put?: never;
        /**
         * Submit Catalogue Scan
         * @description Evaluate a structured listing. The non-image ingestion path, in its own right.
         */
        post: operations["submit_catalogue_scan_scans_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/scans/image": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Submit Image Scan
         * @description Evaluate a photographed package, or return a capture instruction.
         *
         *     A rejected capture is a 201 with no verdict, not an error: the submission was accepted
         *     and stored, and what came back is an instruction rather than a finding. The scan stays
         *     at RECEIVED, whose meaning is exactly that — accepted, evaluation not started.
         */
        post: operations["submit_image_scan_scans_image_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/scans/{scan_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Scan
         * @description One scan in full.
         *
         *     404 both for a scan that does not exist and for one outside this officer's
         *     jurisdiction. That is not laziness about the difference: a 403 would confirm to an
         *     officer in one state that a package is under examination in another, which is
         *     enforcement activity they have no right to know of.
         */
        get: operations["get_scan_scans__scan_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/scans/{scan_id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Review Scan
         * @description Record an officer's action on a verdict. **The only way a scan is ever finalised.**
         *
         *     Nothing else in the application constructs a review, so there is no automated path to
         *     a finalised scan — not a background job, not a re-evaluation, not the submit route.
         *     Confirming, rejecting or overriding is something a person does, and this is where they
         *     do it.
         */
        post: operations["review_scan_scans__scan_id__review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/reviews": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Submit Review
         * @description Persist one anonymous sentiment and report only its publication state.
         */
        post: operations["submit_review_reviews_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/reviews/{product_identifier}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Published Reviews
         * @description Return only published sentiment aggregates for one product identifier.
         */
        get: operations["get_published_reviews_reviews__product_identifier__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/analytics/by-rule": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Aggregate By Rule
         * @description Return privacy-eligible distinct-scan cohorts for failing findings by rule.
         */
        get: operations["aggregate_by_rule_analytics_by_rule_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/analytics/by-category": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Aggregate By Category
         * @description Return privacy-eligible potential-verdict cohorts by confirmed category.
         */
        get: operations["aggregate_by_category_analytics_by_category_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/analytics/over-time": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Aggregate Over Time
         * @description Return privacy-eligible potential-verdict cohorts by UTC evaluation day.
         */
        get: operations["aggregate_over_time_analytics_over_time_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/analytics/jurisdiction": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Aggregate By Jurisdiction
         * @description Return privacy-eligible potential-verdict cohorts by scan jurisdiction.
         */
        get: operations["aggregate_by_jurisdiction_analytics_jurisdiction_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/complaints": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Complaints
         * @description Complaint rows this officer may see, newest first.
         *
         *     The jurisdiction predicate is applied by the repository on every query and is not
         *     something a caller can widen — there is no jurisdiction parameter on this route.
         */
        get: operations["list_complaints_complaints_get"];
        put?: never;
        /**
         * Raise Complaint
         * @description Open an escalation against the manufacturer named on a scan's confirmed verdict.
         *
         *     Three refusals, and they mean different things. A scan this officer cannot see is a 404.
         *     A scan no officer has finalised, or one whose effective verdict is not
         *     POTENTIAL_VIOLATION, is a 409 — the scan is real and visible, and there is simply
         *     nothing here to escalate yet. Text that would put a legal determination in an
         *     external-facing summary is a 422 against the request that carried it.
         */
        post: operations["raise_complaint_complaints_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/complaints/{complaint_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Complaint
         * @description One complaint, with the escalation history recorded against its scan.
         *
         *     The history is every complaint row for that scan, oldest first — which is what the table
         *     holds. Reconstructing separate threads out of the ``supersedes_id`` chains is a reading
         *     the caller can make from the rows; it is not one this route makes for them.
         */
        get: operations["get_complaint_complaints__complaint_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/vendors": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Vendors
         * @description Vendors this officer may see, by name.
         *
         *     The jurisdiction predicate is applied by the repository on every query and is not
         *     something a caller can widen — there is no jurisdiction parameter on this route.
         */
        get: operations["list_vendors_vendors_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/vendors/{vendor_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Vendor
         * @description One vendor in full, or a 404 for absent and out-of-jurisdiction alike.
         */
        get: operations["get_vendor_vendors__vendor_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** Body_issue_access_token_auth_token_post */
        Body_issue_access_token_auth_token_post: {
            /** Grant Type */
            grant_type?: string | null;
            /** Username */
            username: string;
            /**
             * Password
             * Format: password
             */
            password: string;
            /**
             * Scope
             * @default
             */
            scope: string;
            /** Client Id */
            client_id?: string | null;
            /**
             * Client Secret
             * Format: password
             */
            client_secret?: string | null;
        };
        /** Body_submit_image_scan_scans_image_post */
        Body_submit_image_scan_scans_image_post: {
            /** Image */
            image: string;
            /** @default none */
            calibration_method: components["schemas"]["CalibrationMethod"];
            /** Reference Type */
            reference_type?: string | null;
            /** Artwork Dpi */
            artwork_dpi?: number | null;
            product_category?: components["schemas"]["ProductCategory"] | null;
            /**
             * Institutional Or Industrial Confirmed
             * @default false
             */
            institutional_or_industrial_confirmed: boolean;
        };
        /**
         * CalibrationMethod
         * @description What basis, if any, exists for a physical measurement of this scan.
         *
         *     Recorded at capture because it decides whether a millimetre figure may be emitted at
         *     all. Typed rather than buried in :attr:`Scan.capture_metadata` for that reason — a
         *     value that gates a legal output is queryable and constrained, not a key in a blob.
         * @enum {string}
         */
        CalibrationMethod: "artwork" | "reference_object" | "none";
        /**
         * CatalogueRecord
         * @description A structured product listing, as the second ingestion path alongside an image.
         *
         *     E-commerce listings arrive as fields rather than pixels. Accepting them as a
         *     first-class type rather than rendering them into something image-shaped keeps the
         *     connection to any particular marketplace an adapter concern.
         */
        CatalogueRecord: {
            /** Listing Id */
            listing_id: string;
            /** Platform */
            platform: string;
            /**
             * Retrieved At
             * Format: date-time
             */
            retrieved_at: string;
            /**
             * Title
             * @default
             */
            title: string;
            /** Declared Fields */
            declared_fields?: {
                [key: string]: string;
            };
            /** Seller Name */
            seller_name?: string | null;
            /**
             * Image Urls
             * @default []
             */
            image_urls: string[];
        };
        /**
         * CatalogueScanRequest
         * @description The listing ingestion path. A first-class input, not an adapter over the image one.
         */
        CatalogueScanRequest: {
            record: components["schemas"]["CatalogueRecord"];
            product_category?: components["schemas"]["ProductCategory"] | null;
            /**
             * Institutional Or Industrial Confirmed
             * @default false
             */
            institutional_or_industrial_confirmed: boolean;
        };
        /**
         * CategoryAggregateCell
         * @description A privacy-eligible count of scans for a confirmed-category display bucket.
         */
        CategoryAggregateCell: {
            /** Product Category */
            product_category: string;
            /** Count */
            count: number;
        };
        /**
         * CategoryProposal
         * @description A product category a reader inferred, with the evidence it inferred it from.
         *
         *     **A proposal is not a confirmation, and this type exists so the two cannot be
         *     confused.** :class:`~app.contracts.enums.ProductCategory` on its own is the officer's
         *     confirmed category — the thing the sector dispatch keys on, which moves obligations
         *     to another Act. Nothing here may be passed where that is expected. An extraction
         *     reader proposes; an officer confirms; only the confirmation routes.
         *
         *     Every field is required and every one is constrained, so a proposal that cites no
         *     evidence cannot be constructed at all rather than being discouraged by convention. A
         *     category assertion with nothing behind it is the input that would let a guess reach
         *     routing by looking like a reading.
         */
        CategoryProposal: {
            category: components["schemas"]["ProductCategory"];
            /** Confidence */
            confidence: number;
            /** Span Refs */
            span_refs: string[];
            /** Reason */
            reason: string;
        };
        /**
         * ComplaintRaiseRequest
         * @description What an officer supplies to open an escalation against a manufacturer.
         *
         *     Carries no officer identity and no status: the first is the principal's, and the second
         *     is RAISED by construction — ``ComplaintService.raise_complaint`` is the only way a first
         *     row is written, and it names the status itself.
         */
        ComplaintRaiseRequest: {
            /**
             * Scan Id
             * Format: uuid
             */
            scan_id: string;
            /** Manufacturer Name */
            manufacturer_name: string;
            /** Rule Id */
            rule_id: string;
            field: components["schemas"]["DeclarationField"];
            /** Measured Value */
            measured_value: string;
            /** Required Value */
            required_value: string;
        };
        /**
         * ComplaintResponse
         * @description One complaint row, which is one event in an append-only thread.
         *
         *     ``status`` is the state *this row* asserts, not a field that moved, and
         *     ``supersedes_id`` names the row it replaced where it replaced one. Both rows stay.
         */
        ComplaintResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Scan Id
             * Format: uuid
             */
            scan_id: string;
            /**
             * Verdict Id
             * Format: uuid
             */
            verdict_id: string;
            /** Manufacturer Name */
            manufacturer_name: string;
            /** Issue Summary */
            issue_summary: string;
            status: components["schemas"]["ComplaintStatus"];
            /** Raised By Officer Id */
            raised_by_officer_id: string;
            /**
             * Raised At
             * Format: date-time
             */
            raised_at: string;
            /** Supersedes Id */
            supersedes_id?: string | null;
        };
        /**
         * ComplaintStatus
         * @description Where an escalation had got to when the row carrying it was written.
         * @enum {string}
         */
        ComplaintStatus: "raised" | "acknowledged" | "resolved" | "rejected";
        /**
         * ComplaintThread
         * @description One complaint and the escalation history recorded against its scan, oldest first.
         */
        ComplaintThread: {
            complaint: components["schemas"]["ComplaintResponse"];
            /** History */
            history: components["schemas"]["ComplaintResponse"][];
        };
        /**
         * ConsumerSafetyClaim
         * @description What one member of the public asserted about one product. **Not a verdict.**
         *
         *     :class:`app.contracts.Verdict` is what this system recommends about a package and is
         *     PASS / REVIEW / POTENTIAL_VIOLATION for the reasons stated there. This is a consumer
         *     reporting their own experience, stored so it can be republished as theirs. The name
         *     carries that boundary rather than a docstring alone, because a column name survives
         *     into every downstream surface a docstring cannot follow.
         *
         *     It is defined here and deliberately **not** in ``contracts``: ``contracts`` holds the
         *     vocabularies that cross a module boundary, so keeping this out of it means nothing in
         *     the verdict path can import this enum and therefore nothing in the verdict path can
         *     branch on it.
         *
         *     Its values are lowercase against ``Verdict``'s uppercase, which is free structural
         *     separation — in a dump, a CSV export or a log line the two vocabularies are visually
         *     distinct and no string comparison can match across them.
         * @enum {string}
         */
        ConsumerSafetyClaim: "safe" | "unsafe";
        /**
         * DailyAggregateCell
         * @description A privacy-eligible count of scans evaluated on one calendar day.
         */
        DailyAggregateCell: {
            /**
             * Day
             * Format: date
             */
            day: string;
            /** Count */
            count: number;
        };
        /**
         * DeclarationField
         * @description The declarations a package must bear, one member per obligation.
         *
         *     Clause letters are taken from the Legal Metrology (Packaged Commodities) Rules 2011
         *     as consolidated in ``rules-corpus/``. One member per clause, not per role: Rule
         *     6(1)(a) is a single obligation covering manufacturer, packer and importer, and by
         *     Explanation II the marketer or brand owner as well. Which role a given declaration
         *     was made under is a property of the extracted value, not a separate obligation.
         * @enum {string}
         */
        DeclarationField: "NAME_AND_ADDRESS" | "COUNTRY_OF_ORIGIN" | "COMMON_OR_GENERIC_NAME" | "NET_QUANTITY" | "MANUFACTURE_DATE" | "BEST_BEFORE_DATE" | "RETAIL_SALE_PRICE" | "DIMENSIONS" | "OTHER_PRESCRIBED_MATTER" | "CONSUMER_CARE" | "UNIT_SALE_PRICE";
        /**
         * DisplayCategory
         * @enum {string}
         */
        DisplayCategory: "packaged_food" | "cosmetics" | "non_food_packaged_goods" | "electronics" | "household";
        /** DisplayCategoryTaxonomy */
        DisplayCategoryTaxonomy: {
            category: components["schemas"]["DisplayCategory"];
            parent_category: components["schemas"]["DisplayCategory"] | null;
            /** Path */
            path: string[];
            /** Confidence */
            confidence: number;
            /** Span Refs */
            span_refs: string[];
            /** Reason */
            reason: string;
        };
        /**
         * FieldFinding
         * @description The outcome of evaluating one declaration against one rule, with its evidence.
         */
        FieldFinding: {
            field: components["schemas"]["DeclarationField"];
            state: components["schemas"]["FieldState"];
            rule_snapshot: components["schemas"]["RuleParameterSnapshot"];
            /** Observed Value */
            observed_value?: string | null;
            /** Expected Value */
            expected_value?: string | null;
            /** Reason */
            reason: string;
            /**
             * Evidence Span Ids
             * @default []
             */
            evidence_span_ids: string[];
        };
        /**
         * FieldState
         * @description The outcome of evaluating one declaration field against one rule.
         *
         *     Five states, deliberately. Four would force "we could not read it" and "it is not
         *     there" into the same bucket.
         * @enum {string}
         */
        FieldState: "PASS" | "FAIL" | "REVIEW_REQUIRED" | "NOT_APPLICABLE" | "INSUFFICIENT_EVIDENCE";
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        JsonValue: unknown;
        /**
         * Jurisdiction
         * @description The territory an officer's authority runs over.
         *
         *     Levels below the officer's tier are ``None`` — a state-level officer has no single
         *     region, and saying so with ``None`` is what lets :func:`scope_to_jurisdiction` filter
         *     on exactly the levels that are pinned.
         */
        Jurisdiction: {
            /** State */
            state: string;
            /** Region */
            region?: string | null;
            /** District */
            district?: string | null;
        };
        /**
         * JurisdictionAggregateCell
         * @description A privacy-eligible jurisdiction aggregate with a relative density band.
         */
        JurisdictionAggregateCell: {
            /** State */
            state: string;
            /** Region */
            region?: string | null;
            /** District */
            district?: string | null;
            /** Count */
            count: number;
            /** Density Band */
            density_band: string;
        };
        /**
         * ProductCategory
         * @description A *confirmed* product category that a sector override may key on.
         *
         *     Confirmed is the operative word. A category is an input to routing, never an
         *     inference this system makes: routing a package to another Act because a classifier
         *     guessed at its category would move a real legal obligation on a guess. A caller with
         *     no confirmed category passes ``None`` and the packaged rules apply unchanged.
         *
         *     A member exists here because a gazette names that sector and routes an obligation
         *     away from these Rules for it — not because the sector is commercially interesting.
         *     Adding one is adding a routing target, so it comes with the provision that does the
         *     routing.
         *
         *     The values are lowercase where every other vocabulary in this package is upper. That
         *     is deliberate and not to be tidied: they are the ``sector`` keys in the rule store's
         *     ``rules.yaml`` and the strings already written to ``scans.product_category``. Changing
         *     the case would stop the sector dispatch matching any rule while every type check still
         *     passed.
         *
         *     A proposal is not a confirmation. :class:`~app.contracts.evidence.CategoryProposal`
         *     carries a category a reader inferred, and it is a distinct type precisely so it cannot
         *     be passed where this one is expected.
         * @enum {string}
         */
        ProductCategory: "food" | "cosmetics" | "medical_device";
        /**
         * PublishedConsensus
         * @description A published count for one exact consumer sentiment value.
         */
        PublishedConsensus: {
            consumer_safety_claim: components["schemas"]["ConsumerSafetyClaim"];
            /** Submission Count */
            submission_count: number;
        };
        /**
         * PublishedReviewsResponse
         * @description Published consumer sentiment aggregates for one product identifier.
         */
        PublishedReviewsResponse: {
            /** Product Identifier */
            product_identifier: string;
            /** Published Consensus */
            published_consensus: components["schemas"]["PublishedConsensus"][];
        };
        /**
         * QualityReason
         * @enum {string}
         */
        QualityReason: "PASS" | "BLUR_EXCEEDED" | "GLARE_EXCEEDED" | "IMAGE_EMPTY" | "INCOMPLETE_LABEL";
        /**
         * QualityRejection
         * @description A capture the gate refused, and what the officer should do about it.
         *
         *     Deliberately not a verdict and not convertible into one. It carries no findings and no
         *     ``Verdict`` member, so there is no shape in which a rejected capture reaches an
         *     officer looking like a conclusion about the package.
         */
        QualityRejection: {
            reason_code: components["schemas"]["QualityReason"];
            /** Instruction */
            instruction: string;
            /** Blur Score */
            blur_score: number;
            /** Glare Ratio */
            glare_ratio: number;
            /** Coverage Ratio */
            coverage_ratio: number;
        };
        /**
         * ReviewAction
         * @description What an officer did to a verdict. The human confirmation step, as a vocabulary.
         *
         *     Three of these finalise and two do not, and the difference is the whole point of the
         *     table: no automated path may reach a finalised state, so finalisation is the existence
         *     of a row carrying one of the first three actions and is never a column somewhere that
         *     a background job could set.
         * @enum {string}
         */
        ReviewAction: "confirm" | "reject" | "override" | "annotate" | "request_recapture";
        /**
         * ReviewRequest
         * @description An officer's action on a verdict.
         */
        ReviewRequest: {
            action: components["schemas"]["ReviewAction"];
            /** Note */
            note?: string | null;
            overridden_verdict?: components["schemas"]["Verdict"] | null;
            /** Supersedes Id */
            supersedes_id?: string | null;
        };
        /**
         * ReviewResponse
         * @description The review as recorded.
         */
        ReviewResponse: {
            /** Rule Set Version */
            rule_set_version: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Scan Id
             * Format: uuid
             */
            scan_id: string;
            /**
             * Verdict Id
             * Format: uuid
             */
            verdict_id: string;
            action: components["schemas"]["ReviewAction"];
            /** Officer Id */
            officer_id: string;
            /** Note */
            note: string | null;
            overridden_verdict: components["schemas"]["Verdict"] | null;
            /** Supersedes Id */
            supersedes_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Finalised */
            finalised: boolean;
        };
        /**
         * ReviewSubmissionRequest
         * @description Anonymous sentiment submitted for one normalized product identifier.
         */
        ReviewSubmissionRequest: {
            /** Product Identifier */
            product_identifier: string;
            consumer_safety_claim: components["schemas"]["ConsumerSafetyClaim"];
        };
        /**
         * ReviewSubmissionResponse
         * @description Public result of accepting one anonymous sentiment submission.
         */
        ReviewSubmissionResponse: {
            /** Product Identifier */
            product_identifier: string;
            consumer_safety_claim: components["schemas"]["ConsumerSafetyClaim"];
            /**
             * Publication Status
             * @enum {string}
             */
            publication_status: "HELD" | "PUBLISHED";
        };
        /**
         * RuleAggregateCell
         * @description A privacy-eligible count of scans with a failing finding for one rule.
         */
        RuleAggregateCell: {
            /** Rule Id */
            rule_id: string;
            /** Count */
            count: number;
        };
        /**
         * RuleParameterSnapshot
         * @description The rule as it stood at the moment of evaluation, copied by value.
         *
         *     Not a reference to a rule row. The values are duplicated in because a rule set is
         *     published, amended and republished, and a verdict must keep meaning what it meant
         *     when it was issued. Joining a stored verdict back to a live rules table would
         *     re-adjudicate history: an amendment landing on Tuesday would silently change what
         *     Monday's scan is recorded as having found, and the officer who signed off on Monday's
         *     finding would have no way to see that it had moved.
         *
         *     Build these with :meth:`from_rule` so the copy cannot be skipped by accident.
         */
        RuleParameterSnapshot: {
            /** Rule Id */
            rule_id: string;
            /** Clause Ref */
            clause_ref: string;
            /** Gazette Ref */
            gazette_ref: string;
            /** Source Text */
            source_text: string;
            status: components["schemas"]["RuleStatus"];
            severity: components["schemas"]["RuleSeverity"];
            /** Rule Set Version */
            rule_set_version: string;
            /** Parameters */
            parameters: {
                [key: string]: components["schemas"]["JsonValue"];
            };
            /** Rounding Increment */
            rounding_increment: string | null;
            /** Tolerance */
            tolerance: string | null;
            tolerance_basis: components["schemas"]["ToleranceBasis"] | null;
        };
        /**
         * RuleSeverity
         * @description How a breach of this rule routes in the officer workflow.
         *
         *     Operational routing, not a legal grading. No gazette grades contraventions by
         *     severity, so this must not be presented to an officer as a statement about how
         *     serious a breach is in law.
         * @enum {string}
         */
        RuleSeverity: "MANDATORY" | "CONDITIONAL" | "ADVISORY";
        /**
         * RuleStatus
         * @description Whether an encoded rule has been checked against its gazette source.
         * @enum {string}
         */
        RuleStatus: "VERIFIED" | "UNVERIFIED";
        /**
         * ScanDetail
         * @description One scan in full: its findings, or the capture instruction that replaced them.
         */
        ScanDetail: {
            /** Rule Set Version */
            rule_set_version: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            source_type: components["schemas"]["ScanSourceType"];
            status: components["schemas"]["ScanStatus"];
            verdict?: components["schemas"]["Verdict"] | null;
            /** Product Category */
            product_category?: string | null;
            /** Officer Id */
            officer_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Finalised */
            finalised: boolean;
            /** Subject Ref */
            subject_ref?: string | null;
            /** Evaluated At */
            evaluated_at?: string | null;
            /**
             * Findings
             * @default []
             */
            findings: components["schemas"]["FieldFinding"][];
            quality?: components["schemas"]["QualityRejection"] | null;
            category_proposal?: components["schemas"]["CategoryProposal"] | null;
            display_category?: components["schemas"]["DisplayCategoryTaxonomy"] | null;
        };
        /**
         * ScanSourceType
         * @description Which ingestion path a scan arrived by.
         *
         *     Both are first-class. A listing is not an image that failed to be an image, and
         *     modelling it as its own source type is what keeps a marketplace adapter an adapter.
         * @enum {string}
         */
        ScanSourceType: "physical_label" | "catalogue_record";
        /**
         * ScanStatus
         * @description Where a scan has got to. Processing state, never a compliance outcome.
         * @enum {string}
         */
        ScanStatus: "received" | "processing" | "complete" | "failed";
        /**
         * ScanSummary
         * @description One scan as it appears in a list. No findings — those are on the detail route.
         */
        ScanSummary: {
            /** Rule Set Version */
            rule_set_version: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            source_type: components["schemas"]["ScanSourceType"];
            status: components["schemas"]["ScanStatus"];
            verdict?: components["schemas"]["Verdict"] | null;
            /** Product Category */
            product_category?: string | null;
            /** Officer Id */
            officer_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Finalised */
            finalised: boolean;
        };
        /**
         * Token
         * @description The token response, in the shape the OAuth2 password flow specifies.
         */
        Token: {
            /** Access Token */
            access_token: string;
            /**
             * Token Type
             * @default bearer
             */
            token_type: string;
        };
        /**
         * ToleranceBasis
         * @description How a rule's tolerance figure is to be read.
         *
         *     ``Decimal("0.05")`` alone is ambiguous: five paise, or five percent. The Rules use
         *     both — the First Schedule states maximum permissible error as a percentage of the
         *     declared quantity, while a money tolerance is an absolute amount.
         * @enum {string}
         */
        ToleranceBasis: "ABSOLUTE" | "PERCENTAGE";
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /**
         * VendorResponse
         * @description One premises on the register.
         *
         *     Carries no scan counts and no verdict summary. A vendor-submitted scan is an ordinary
         *     scan, and :class:`~app.core.market.VendorScanRow` holds nothing the evaluation path
         *     could branch on; a vendor's compliance history is a question for the scan routes, which
         *     are scoped in their own right.
         */
        VendorResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            vendor_type: components["schemas"]["VendorType"];
            jurisdiction: components["schemas"]["Jurisdiction"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /**
         * VendorType
         * @description What kind of premises a vendor operates.
         *
         *     Three, because three is what the pilot distinguishes. This says nothing about
         *     obligations: a kirana and a supermarket are under identical declaration rules, and
         *     nothing in the verdict path reads this column.
         * @enum {string}
         */
        VendorType: "godown" | "supermarket" | "kirana";
        /**
         * Verdict
         * @description The package-level recommendation assembled from the per-field findings.
         *
         *     Three members. The system recommends and a human confirms, so there is no member for
         *     a confirmed breach — no "violation confirmed", no "non-compliant". Adding one would
         *     make the software issue a legal determination it has no standing to issue.
         * @enum {string}
         */
        Verdict: "PASS" | "REVIEW" | "POTENTIAL_VIOLATION";
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    issue_access_token_auth_token_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/x-www-form-urlencoded": components["schemas"]["Body_issue_access_token_auth_token_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Token"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_scans_scans_get: {
        parameters: {
            query?: {
                product?: string | null;
                manufacturer?: string | null;
                status?: components["schemas"]["ScanStatus"] | null;
                created_from?: string | null;
                created_to?: string | null;
                limit?: number;
                offset?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScanSummary"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    submit_catalogue_scan_scans_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CatalogueScanRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScanDetail"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    submit_image_scan_scans_image_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_submit_image_scan_scans_image_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScanDetail"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_scan_scans__scan_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                scan_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScanDetail"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    review_scan_scans__scan_id__review_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                scan_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    submit_review_reviews_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewSubmissionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewSubmissionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_published_reviews_reviews__product_identifier__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                product_identifier: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PublishedReviewsResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    aggregate_by_rule_analytics_by_rule_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RuleAggregateCell"][];
                };
            };
        };
    };
    aggregate_by_category_analytics_by_category_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CategoryAggregateCell"][];
                };
            };
        };
    };
    aggregate_over_time_analytics_over_time_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DailyAggregateCell"][];
                };
            };
        };
    };
    aggregate_by_jurisdiction_analytics_jurisdiction_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JurisdictionAggregateCell"][];
                };
            };
        };
    };
    list_complaints_complaints_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComplaintResponse"][];
                };
            };
        };
    };
    raise_complaint_complaints_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ComplaintRaiseRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComplaintResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_complaint_complaints__complaint_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                complaint_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ComplaintThread"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_vendors_vendors_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VendorResponse"][];
                };
            };
        };
    };
    get_vendor_vendors__vendor_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                vendor_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VendorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
