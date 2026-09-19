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
         * @description Accept a photographed package and evaluate it after this response has gone.
         *
         *     The last seven fields are :class:`PackageConfirmations` — what the officer has
         *     established about the package that no photograph can: which limb of Rule 7(4) sizes
         *     the panel, whether Rule 7(5) disapplies Rule 7's sizing, whether a Rule 33 relaxation
         *     has been recorded, and where on the capture the principal display panel is. Each
         *     defaults to confirming nothing. The panel mark is four numbers in the uploaded image's
         *     own pixels, all four or none; a partial mark is a malformed request, and so is one
         *     that runs off the image.
         *
         *     The response is the scan at PROCESSING with no verdict: the row a client polls
         *     ``GET /scans/{id}`` against until the status moves. Evaluation is not awaited here
         *     because it is an OCR run of the better part of a minute on CPU, and a request that
         *     sits silent for that long does not survive a phone on a mobile network — the carrier
         *     path drops it around twenty-five seconds in, the browser reports "failed to fetch",
         *     and the verdict that was written a moment later is never seen.
         *
         *     What evaluation reports is stored, not returned: a verdict and its findings in their
         *     tables, and the capture instruction, category proposal and display category as the
         *     scan's :class:`~app.pipeline.schemas.CaptureOutcome`. A rejected capture is not an
         *     error: the scan returns to RECEIVED with the instruction attached, which is exactly
         *     what happened — accepted, and no evaluation made of the package.
         */
        post: operations["submit_image_scan_scans_image_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/scans/artwork": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Submit Artwork Scan
         * @description Accept pre-print artwork of the principal display panel — a PDF or an SVG.
         *
         *     The one path on which a millimetre is exact: the file states its own physical size, so
         *     every measurement is :class:`~app.contracts.MeasurementExact` and no calibration is
         *     asked for. Same shape as the image route otherwise — the scan is returned at
         *     PROCESSING and polled, because the render is still read by OCR.
         *
         *     Stored with :attr:`~app.core.CalibrationMethod.ARTWORK`, which is the typed field that
         *     already means "physical sizes are known exactly", and the file type beside it in
         *     ``capture_metadata``. The file is held so a category confirmation can evaluate it
         *     again, exactly as a photograph is.
         */
        post: operations["submit_artwork_scan_scans_artwork_post"];
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
    "/scans/{scan_id}/category": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Confirm Category
         * @description Confirm a scan's product category, and evaluate its capture again under it.
         *
         *     Returns a **new** scan carrying the confirmed category — for a photograph, at
         *     PROCESSING, to be polled like any submission. The original is left exactly as it was.
         *     An officer act: it sits behind the officer principal, and nothing the pipeline read —
         *     no proposal, no display classification — is consulted here or can stand in for the
         *     body's ``product_category``.
         */
        post: operations["confirm_category_scans__scan_id__category_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/scans/{scan_id}/evidence": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Read Evidence
         * @description The scan's evidence chain, verified now, on this read.
         */
        get: operations["read_evidence_scans__scan_id__evidence_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/scans/{scan_id}/evidence/report": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Export Report
         * @description Issue the BSA s.63(4) Part A certificate (``json``) or the filed report (``pdf``, ``docx``).
         *
         *     A POST, because issuing a report is an event the chain records: the export's digest and
         *     the officer who took it are appended as the next entry. Refused with 409 until an
         *     officer has finalised the review, and refused outright if the chain does not verify.
         */
        post: operations["export_report_scans__scan_id__evidence_report_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/consumer/scans/image": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Submit Consumer Image Scan
         * @description Accept a consumer's photograph of a label; poll ``GET /consumer/scans/{id}``.
         *
         *     Uncalibrated and uncategorised by construction: a consumer confirms no product
         *     category and places no reference object, so the packaged rules apply unchanged and
         *     no physical measurement is ever reported from their photograph.
         */
        post: operations["submit_consumer_image_scan_consumer_scans_image_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/consumer/scans/{scan_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Consumer Scan
         * @description One consumer scan in full. An officer's scan is a 404 here, by jurisdiction.
         */
        get: operations["get_consumer_scan_consumer_scans__scan_id__get"];
        put?: never;
        post?: never;
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
    "/complaints/{complaint_id}/transitions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Transition Complaint
         * @description Acknowledge, resolve or reject an escalation, as a new row superseding this one.
         *
         *     A complaint this officer cannot see is a 404. A move the domain's transition table does
         *     not allow — out of a closed thread, or back to RAISED — is a 409, and so is a row that a
         *     later row already supersedes: transitioning anything but the head would fork the thread.
         *     That last refusal is ``uq_complaints_supersedes_id`` and nothing else — there is no
         *     look-before-write in front of it, because a check two officers can both pass at the same
         *     moment guards nothing the constraint does not, and the constraint also holds then.
         */
        post: operations["transition_complaint_complaints__complaint_id__transitions_post"];
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
        /**
         * Register Vendor
         * @description Put a premises on the register with a login, inside the officer's own territory.
         */
        post: operations["register_vendor_vendors_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/vendors/auth/token": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Issue Vendor Token
         * @description Exchange a vendor's username and password for a vendor token.
         */
        post: operations["issue_vendor_token_vendors_auth_token_post"];
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
    "/vendor/scans/image": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Submit Vendor Image Scan
         * @description A vendor photographs a package on their own shelf; poll ``GET /vendor/scans/{id}``.
         *
         *     No category and no calibration: a vendor confirms nothing. The officer covering the
         *     premises confirms the category on the scan the vendor filed, as on any other.
         */
        post: operations["submit_vendor_image_scan_vendor_scans_image_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/vendor/scans": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Vendor Scans
         * @description This vendor's own submissions, newest first, and nobody else's.
         */
        get: operations["list_vendor_scans_vendor_scans_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/vendor/scans/{scan_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Vendor Scan
         * @description One of this vendor's scans. Another vendor's, or an officer's, is a 404.
         */
        get: operations["get_vendor_scan_vendor_scans__scan_id__get"];
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
        /** Body_issue_vendor_token_vendors_auth_token_post */
        Body_issue_vendor_token_vendors_auth_token_post: {
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
        /** Body_submit_artwork_scan_scans_artwork_post */
        Body_submit_artwork_scan_scans_artwork_post: {
            /** Artwork */
            artwork: string;
            product_category?: components["schemas"]["ProductCategory"] | null;
            /**
             * Institutional Or Industrial Confirmed
             * @default false
             */
            institutional_or_industrial_confirmed: boolean;
            /** Ward */
            ward?: string | null;
            /** @default rectangular */
            package_shape: components["schemas"]["PackageShape"];
            /**
             * Declarations Required Under Other Law
             * @default false
             */
            declarations_required_under_other_law: boolean;
            /**
             * Rule 33 Relaxation Granted
             * @default false
             */
            rule_33_relaxation_granted: boolean;
        };
        /** Body_submit_consumer_image_scan_consumer_scans_image_post */
        Body_submit_consumer_image_scan_consumer_scans_image_post: {
            /** Image */
            image: string;
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
            /** Ward */
            ward?: string | null;
            /** @default rectangular */
            package_shape: components["schemas"]["PackageShape"];
            /**
             * Declarations Required Under Other Law
             * @default false
             */
            declarations_required_under_other_law: boolean;
            /**
             * Rule 33 Relaxation Granted
             * @default false
             */
            rule_33_relaxation_granted: boolean;
            /** Panel X */
            panel_x?: number | null;
            /** Panel Y */
            panel_y?: number | null;
            /** Panel Width */
            panel_width?: number | null;
            /** Panel Height */
            panel_height?: number | null;
        };
        /** Body_submit_vendor_image_scan_vendor_scans_image_post */
        Body_submit_vendor_image_scan_vendor_scans_image_post: {
            /** Image */
            image: string;
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
            /** Ward */
            ward?: string | null;
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
         * CategoryConfirmation
         * @description An officer's answer to "which product category is this package".
         *
         *     One required field and nothing else is accepted. There is no ``accept_proposal`` flag
         *     and no default: the category has to be stated in the request by the officer making it,
         *     so there is no spelling of this body that means "whatever the pipeline read".
         */
        CategoryConfirmation: {
            product_category: components["schemas"]["ProductCategory"];
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
        /** ChainVerification */
        ChainVerification: {
            /** Is Valid */
            is_valid: boolean;
            /** Broken Link Index */
            broken_link_index?: number | null;
            /**
             * Purged Indices
             * @default []
             */
            purged_indices: number[];
            /** Reason */
            reason?: ("payload_hash_mismatch" | "previous_hash_mismatch" | "ordering_violation" | "entry_hash_mismatch" | "missing_genesis" | "corrupted_timestamp") | null;
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
            /** Note */
            note?: string | null;
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
         * ComplaintTransitionRequest
         * @description What an officer supplies to move an escalation on: the new state, and their words.
         *
         *     Carries no officer identity — that is the principal's — and no ``supersedes_id``: the
         *     row being transitioned is named by the URL, and the new row supersedes exactly that one.
         *     RAISED is not refused here; the domain's transition table refuses it, with every other
         *     illegal move, so there is one definition of which moves exist.
         */
        ComplaintTransitionRequest: {
            status: components["schemas"]["ComplaintStatus"];
            /** Note */
            note?: string | null;
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
        /** EntrySummary */
        EntrySummary: {
            /** Sequence */
            sequence: number;
            /** Timestamp */
            timestamp: string;
            /** Entry Hash */
            entry_hash: string;
            asset_type: components["schemas"]["EvidenceAssetType"];
            /** Is Purged */
            is_purged: boolean;
        };
        /**
         * EvidenceAssetType
         * @description What a stored piece of evidence *is*, for the purpose of deciding when it is destroyed.
         *
         *     The counterpart to :class:`EvidenceProvider`, which records what produced a piece of
         *     evidence. This records what the thing is, and it is the field a retention window is
         *     read from — so it is inside :func:`app.modules.evidence.chain.compute_entry_hash`.
         *     Outside the hash an entry could be relabelled, fall under a different retention rule,
         *     and chain verification would still report the chain intact.
         *
         *     Deliberately short. A member ships only alongside something that consumes it — a
         *     retention window, a purge branch, or a hash input — so this is the set the retention
         *     rules actually distinguish today and not a complete taxonomy of evidence. Adding a
         *     member later needs a hand-written ``ALTER TYPE ... ADD VALUE``, which cannot run inside
         *     a transaction and which ``alembic check`` does not report as drift.
         * @enum {string}
         */
        EvidenceAssetType: "PRODUCT_IMAGE" | "PERSONAL_DATA" | "AUDIT_LOG";
        /**
         * EvidenceView
         * @description A scan's chain, verified on the way out.
         *
         *     ``verification`` is computed on every read and never stored: a stored "valid" flag is
         *     the one thing an attacker who could edit an entry could also edit.
         */
        EvidenceView: {
            /** Scan Id */
            scan_id: string;
            verification: components["schemas"]["ChainVerification"];
            /** Entries */
            entries: components["schemas"]["EntrySummary"][];
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
         * PackageShape
         * @enum {string}
         */
        PackageShape: "rectangular" | "cylindrical" | "other";
        /**
         * PanelSpan
         * @description One run of text as vision read it off the panel, by the id the findings cite.
         *
         *     Validated from the stored evidence record, which carries the whole span; the other
         *     fields are ignored here, not copied, so this stays text and an id read through.
         */
        PanelSpan: {
            /** Span Id */
            span_id: string;
            /** Text */
            text: string;
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
         *     routing. :attr:`NON_CONSUMABLE` is the single exception and says why on itself.
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
        ProductCategory: "food" | "cosmetics" | "medical_device" | "non_consumable";
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
         * RoleTier
         * @description The three structural levels of the enforcement hierarchy, broadest first.
         *
         *     Members are ordered, and the order carries meaning: :attr:`rank` and
         *     :attr:`scope_fields` are both derived from position, so the "each tier is one level
         *     narrower than the one above" property cannot drift out of step with the enum.
         *
         *     Each member's value is the :class:`Jurisdiction` field that tier is pinned to. That
         *     is deliberate — it makes the tier and the column it filters on the same fact, rather
         *     than two facts a future edit could separate.
         * @enum {string}
         */
        RoleTier: "state" | "region" | "district";
        /**
         * RoutingDecision
         * @description Routing outcome for an evaluated vendor submission.
         *
         *     Specifies the target officer tier, whether an on-site physical inspection visit is
         *     required, and whether action is required (or routes as informational).
         */
        RoutingDecision: {
            /** @description The structural enforcement tier whose queue receives this outcome. */
            target_tier: components["schemas"]["RoleTier"];
            /**
             * Requires Visit
             * @description Whether an on-site physical inspection visit is mandated.
             */
            requires_visit: boolean;
            /**
             * Action Required
             * @description True if the result flags for officer action; False if purely informational.
             */
            action_required: boolean;
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
            /** Ward */
            ward?: string | null;
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
            /**
             * Panel Spans
             * @default []
             */
            panel_spans: components["schemas"]["PanelSpan"][];
            quality?: components["schemas"]["QualityRejection"] | null;
            /** Refusal */
            refusal?: string | null;
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
            /** Ward */
            ward?: string | null;
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
         * VendorRegistration
         * @description What an officer supplies to put a premises on the register with a login.
         *
         *     The jurisdiction is the premises', stated in full to the district, because that is what
         *     routes the vendor's scans to an officer: a scan attributed to this vendor is filed in
         *     this territory. The route refuses a territory outside the registering officer's own.
         *     The password is hashed before anything is stored and is never read back.
         */
        VendorRegistration: {
            /** Name */
            name: string;
            vendor_type: components["schemas"]["VendorType"];
            jurisdiction: components["schemas"]["Jurisdiction"];
            /** Username */
            username: string;
            /** Password */
            password: string;
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
         * VendorScanView
         * @description A vendor's own scan, with where it was routed.
         *
         *     ``routing`` says which tier's queue the outcome reached and whether it calls for a
         *     visit; it is ``None`` until the scan has a verdict. The verdict itself is unchanged —
         *     a vendor reads the same recommendation the officer does.
         */
        VendorScanView: {
            scan: components["schemas"]["ScanDetail"];
            routing: components["schemas"]["RoutingDecision"] | null;
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
    submit_artwork_scan_scans_artwork_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_submit_artwork_scan_scans_artwork_post"];
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
    confirm_category_scans__scan_id__category_post: {
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
                "application/json": components["schemas"]["CategoryConfirmation"];
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
    read_evidence_scans__scan_id__evidence_get: {
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
                    "application/json": components["schemas"]["EvidenceView"];
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
    export_report_scans__scan_id__evidence_report_post: {
        parameters: {
            query?: {
                format?: string;
            };
            header?: never;
            path: {
                scan_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
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
    submit_consumer_image_scan_consumer_scans_image_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_submit_consumer_image_scan_consumer_scans_image_post"];
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
    get_consumer_scan_consumer_scans__scan_id__get: {
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
    transition_complaint_complaints__complaint_id__transitions_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                complaint_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ComplaintTransitionRequest"];
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
    register_vendor_vendors_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VendorRegistration"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
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
    issue_vendor_token_vendors_auth_token_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/x-www-form-urlencoded": components["schemas"]["Body_issue_vendor_token_vendors_auth_token_post"];
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
    submit_vendor_image_scan_vendor_scans_image_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_submit_vendor_image_scan_vendor_scans_image_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["VendorScanView"];
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
    list_vendor_scans_vendor_scans_get: {
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
                    "application/json": components["schemas"]["ScanSummary"][];
                };
            };
        };
    };
    get_vendor_scan_vendor_scans__scan_id__get: {
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
                    "application/json": components["schemas"]["VendorScanView"];
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
