from app.db.session_connection import get_connection
from decimal import Decimal

from app.cache.redis_cache import (
    get_json_cache,
    create_cache_key,
    set_json_cache,
)

def serialize_to_float(row: dict) -> dict:
    return{
        key: float(value) if isinstance(value, Decimal) else value for key, value in row.items() 
    }

def search_consortium(consortium_type: str | None = None) -> list[dict]:
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            if consortium_type:
                cur.execute(
                    """
                    SELECT
                        consortium_id,
                        consortium_name,
                        consortium_type,
                        description,
                        credit_amount_min,
                        credit_amount_max,
                        admin_fee_percentage,
                        reserve_fund_percentage,
                        minimum_income,
                        max_term_months,
                        average_monthly_payment_min,
                        average_monthly_payment_max,
                        contemplation_method,
                        risk_level,
                        is_active
                    FROM consortium_options
                    WHERE consortium_type = trim(lower(%s))
                      AND is_active = TRUE
                    ORDER BY consortium_name
                    """,
                    (consortium_type,)
                )
            else:
                cur.execute(
                    """
                    SELECT
                        consortium_id,
                        consortium_code,
                        consortium_name,
                        consortium_type,
                        description,
                        credit_amount_min,
                        credit_amount_max,
                        admin_fee_percentage,
                        reserve_fund_percentage,
                        minimum_income,
                        max_term_months,
                        average_monthly_payment_min,
                        average_monthly_payment_max,
                        contemplation_method,
                        risk_level,
                        is_active
                    FROM consortium_options
                    WHERE is_active = TRUE
                    ORDER BY consortium_name
                    """
                )

            rows = cur.fetchall()
            return [serialize_to_float(dict(row)) for row in rows]
        
    finally:
        conn.close()

def search_consortium_cache(consortium_type: str | None = None) -> list[dict]:

    cache_key = create_cache_key("consortium_db", consortium_type)
    cached_json = get_json_cache(cache_key)

    if cached_json is not None:
        print(f"Redis Cache Hit: {cache_key}", flush=True)
        return cached_json

    print(f"Redis Cache Miss: {cache_key}", flush=True)

    result = search_consortium(consortium_type=consortium_type)

    set_json_cache(
        cache_key,
        result,
        (60 * 30)
    )

    return result

def simulate_consortium_payment(
    credit_amount: float,
    term_months: int,
    total_admin_fee_rate: float,
    reserve_fund_rate: float,
    membership_fee: float,
) -> dict:
    """
    Simulates an estimated consortium monthly payment.

    Important:
    This is a simplified simulation.
    Real consortium installments may vary due to adjustments, group rules,
    insurance, reserve fund changes, and administrator-specific conditions.
    """

    if credit_amount <= 0:
        raise ValueError("credit_amount must be greater than zero")

    if term_months <= 0:
        raise ValueError("term_months must be greater than zero")

    if total_admin_fee_rate < 0:
        raise ValueError("total_admin_fee_rate cannot be negative")

    if reserve_fund_rate < 0:
        raise ValueError("reserve_fund_rate cannot be negative")

    admin_fee_amount = credit_amount * (total_admin_fee_rate / 100)
    reserve_fund_amount = credit_amount * (reserve_fund_rate / 100)

    total_cost = credit_amount + admin_fee_amount + reserve_fund_amount + membership_fee
    estimated_monthly_payment = total_cost / term_months

    return {
        "credit_amount": round(credit_amount, 2),
        "term_months": term_months,
        "total_admin_fee_rate_percent": total_admin_fee_rate,
        "reserve_fund_rate_percent": reserve_fund_rate,
        "membership_fee": round(membership_fee, 2),
        "admin_fee_amount": round(admin_fee_amount, 2),
        "reserve_fund_amount": round(reserve_fund_amount, 2),
        "estimated_total_cost": round(total_cost, 2),
        "estimated_monthly_payment": round(estimated_monthly_payment, 2),
        "important_note": (
            "This is an estimate. Real consortium installments may vary according "
            "to group rules, credit updates, insurance, reserve fund changes, "
            "and administrator conditions."
        ),
    }

def evaluate_consortium_affordability(
    monthly_income: float,
    monthly_existing_debts: float,
    estimated_consortium_payment: float,
) -> dict:
    """
    Evaluates whether a consortium payment appears affordable.

    This is not credit approval.
    It is a basic affordability analysis.
    """

    if monthly_income <= 0:
        raise ValueError("monthly_income must be greater than zero")

    if monthly_existing_debts < 0:
        raise ValueError("monthly_existing_debts cannot be negative")

    if estimated_consortium_payment <= 0:
        raise ValueError("estimated_consortium_payment must be greater than zero")

    current_debt_ratio = monthly_existing_debts / monthly_income
    projected_debt_ratio = (
        monthly_existing_debts + estimated_consortium_payment
    ) / monthly_income

    if projected_debt_ratio < 0.30:
        affordability_level = "comfortable"
    elif projected_debt_ratio < 0.45:
        affordability_level = "attention_required"
    else:
        affordability_level = "high_risk"

    return {
        "monthly_income": round(monthly_income, 2),
        "monthly_existing_debts": round(monthly_existing_debts, 2),
        "estimated_consortium_payment": round(estimated_consortium_payment, 2),
        "current_debt_ratio_percent": round(current_debt_ratio * 100, 2),
        "projected_debt_ratio_percent": round(projected_debt_ratio * 100, 2),
        "affordability_level": affordability_level,
        "important_note": (
            "This is not credit approval and does not guarantee participation, "
            "contemplation, or suitability."
        ),
    }


def evaluate_consortium_suitability(
    objective: str,
    urgency_months: int | None,
    has_bid_amount: bool,
    wants_predictable_acquisition_date: bool,
) -> dict:
    """
    Evaluates whether a consortium is conceptually suitable for the user's objective.

    Consortiums are usually better when the user can wait and does not need
    immediate possession of the good/service.
    """

    objective_lower = objective.lower()

    warnings = []
    suitability_score = 0

    if urgency_months is None:
        warnings.append("The user's acquisition urgency was not provided.")
    elif urgency_months <= 3:
        suitability_score -= 2
        warnings.append(
            "The user appears to need the asset very soon. Consortium may not be ideal."
        )
    elif urgency_months <= 12:
        suitability_score -= 1
        warnings.append(
            "The user has moderate urgency. Consortium may work only if bid strategy is realistic."
        )
    else:
        suitability_score += 2

    if has_bid_amount:
        suitability_score += 1
    else:
        warnings.append(
            "The user did not mention a bid amount. Without a bid, contemplation timing is uncertain."
        )

    if wants_predictable_acquisition_date:
        suitability_score -= 2
        warnings.append(
            "Consortiums usually do not guarantee a predictable acquisition date."
        )
    else:
        suitability_score += 1

    if objective_lower in ["automobile", "motorcycle", "real_estate", "services"]:
        suitability_score += 1

    if suitability_score >= 3:
        suitability = "potentially_suitable"
    elif suitability_score >= 1:
        suitability = "partially_suitable"
    else:
        suitability = "not_ideal"

    return {
        "objective": objective,
        "urgency_months": urgency_months,
        "has_bid_amount": has_bid_amount,
        "wants_predictable_acquisition_date": wants_predictable_acquisition_date,
        "suitability": suitability,
        "warnings": warnings,
        "important_note": (
            "This is a conceptual suitability analysis, not financial, legal, "
            "or credit approval advice."
        ),
    }