class Pagination:
    """
    Simple pluggable pagination class.
    Can be reused in different controllers.
    """

    def __init__(self, page=1, per_page=10):
        self.page = max(page, 1)
        self.per_page = max(per_page, 1)
        self.total = 0

    def paginate(self, records):
        start = (self.page - 1) * self.per_page
        end = start + self.per_page
        return records[start:end]

    def to_response(self, records_count):
        self.total = records_count
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total_records": self.total,
            "total_pages": (self.total // self.per_page)
            + (1 if self.total % self.per_page else 0),
        }
