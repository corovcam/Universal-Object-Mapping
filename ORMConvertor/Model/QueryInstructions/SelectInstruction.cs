using Model.QueryInstructions.Enums;

namespace Model.QueryInstructions;
public sealed record SelectInstruction(
    string? LeftTable,
    string? LeftProperty,
    string? LeftConstant,
    BooleanOperator Operator,
    string? RightTable,
    string? RightProperty,
    string? RightConstant
) : QueryInstruction
{
    public override string Accept(IQueryVisitor visitor) => visitor.Visit(this);
}
