namespace Model.QueryInstructions;

public sealed record FromInstruction(string Table, string? Alias = null) : QueryInstruction
{
    public override string Accept(IQueryVisitor visitor) => visitor.Visit(this);
}
